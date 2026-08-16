import asyncio
import logging
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings, setup_logging
from app.db import AsyncSessionLocal
from app.models.audio_task import AudioTask
from app.models.script import Script
from app.models.setting import Setting
from app.services.audio_postprocessor import probe_audio
from app.services.audio_render_files import final_path
from app.services.audio_renderer import AudioRenderer
from app.services.tts_factory import get_tts_service
from app.utils.time_utils import utc_now

setup_logging()
logger = logging.getLogger(__name__)

MAX_TEXT_LENGTH = 5000
MAX_RETRIES = 1


async def _get_or_create_setting(db: AsyncSession) -> Setting:
    result = await db.execute(select(Setting).where(Setting.id == 1))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = Setting(id=1)
        db.add(setting)
        await db.commit()
    return setting


async def process_task(task_id: int, *, session_factory: async_sessionmaker = AsyncSessionLocal):
    async with session_factory() as db:
        result = await db.execute(select(AudioTask).where(AudioTask.id == task_id))
        task = result.scalar_one()

        result = await db.execute(select(Script).where(Script.id == task.script_id))
        script = result.scalar_one()

        setting = await _get_or_create_setting(db)

        task.status = "processing"
        await db.commit()

        try:
            if task.render_plan is not None:
                await _process_render_task(task, setting, db)
                await db.commit()
                return
            if len(script.content) > MAX_TEXT_LENGTH:
                raise ValueError(
                    f"文本过长（{len(script.content)} 字），当前上限 {MAX_TEXT_LENGTH} 字"
                )

            tts_params = task.tts_params or {}
            tts_config = setting.tts_config or {}
            provider = tts_config.get("provider", "volcano")
            voice_id = tts_params.get("voice_id") or ""
            # 任务级 voice_id 若与当前 provider 的音色命名空间不符（如 Dify 返回的
            # 描述性占位符 female_gentle_01），则回退到全局配置，避免无效音色导致
            # 阿里云/火山引擎调用失败。
            if provider == "aliyun" and voice_id:
                if not (
                    voice_id.startswith("long")
                    or voice_id.startswith("loong")
                    or voice_id.startswith("sambert")
                ):
                    voice_id = ""
            voice_id = voice_id or tts_config.get("voice_id") or ""
            if not voice_id:
                raise ValueError("未配置音色（voice_id）")
            speed = float(tts_params.get("speed", tts_config.get("speed", 1.0)))
            volume = float(tts_params.get("volume", tts_config.get("volume", 1.0)))
            output_format = (
                tts_params.get("output_format") or tts_config.get("output_format") or "mp3"
            )

            logger.info(
                "[AudioWorker] task=%s script=%s provider=%s model=%s voice=%s "
                "text_len=%s speed=%s volume=%s format=%s instruction_len=%s",
                task.id,
                script.id,
                tts_config.get("provider"),
                tts_config.get("model"),
                voice_id,
                len(script.content),
                speed,
                volume,
                output_format,
                len(task.voice_prompt) if isinstance(task.voice_prompt, str) else 0,
            )

            service = get_tts_service(tts_config)
            audio_bytes = await service.synthesize(
                text=script.content,
                voice_id=voice_id,
                speed=speed,
                volume=volume,
                output_format=output_format,
                instruction=task.voice_prompt,
            )

            general_config = setting.general_config or {}
            output_dir = general_config.get("audio_output_dir") or settings.audio_output_dir
            os.makedirs(output_dir, exist_ok=True)
            file_path = os.path.join(output_dir, f"{task.id}.{output_format}")
            with open(file_path, "wb") as f:
                f.write(audio_bytes)

            task.status = "completed"
            task.file_path = file_path
            task.completed_at = utc_now()
            task.error_msg = None
        except Exception as e:
            logger.exception(
                "[AudioWorker] task=%s failed: %s (retry_count=%s)",
                task.id,
                e,
                task.retry_count,
            )
            task.error_msg = str(e)
            if task.retry_count < MAX_RETRIES:
                task.retry_count += 1
                task.status = "pending"
            else:
                task.status = "failed"
        finally:
            await db.commit()


async def _process_render_task(task: AudioTask, setting: Setting, db: AsyncSession) -> None:
    snapshot = task.tts_snapshot or {}
    current_config = setting.tts_config or {}
    if current_config.get("provider", "aliyun") != snapshot.get("provider"):
        raise ValueError("任务供应商凭证不可用：当前配置与任务快照不匹配")
    service_config = {**current_config, **snapshot}
    service = get_tts_service(service_config)
    if not service.is_available():
        raise ValueError("任务对应供应商凭证缺失")
    output_dir = (setting.general_config or {}).get("audio_output_dir") or settings.audio_output_dir
    existing = final_path(task.id, output_dir)
    if existing.is_file():
        try:
            info = probe_audio(existing)
            task.status = "completed"
            task.stage = "completed"
            task.file_path = str(existing)
            task.actual_duration_seconds = info.duration_seconds
            task.completed_at = utc_now()
            task.error_msg = None
            return
        except Exception:
            pass

    async def progress(completed: int, stage: str) -> None:
        task.completed_segments = completed
        task.stage = stage
        await db.commit()

    task.stage = "synthesizing"
    renderer = AudioRenderer(service, output_dir)
    path, duration = await renderer.render(task, progress=progress)
    task.status = "completed"
    task.stage = "completed"
    task.completed_segments = task.total_segments or task.completed_segments
    task.file_path = str(path)
    task.actual_duration_seconds = duration
    task.completed_at = utc_now()
    task.error_msg = None


async def worker_loop(
    concurrency: int = settings.worker_concurrency,
    *,
    session_factory: async_sessionmaker = AsyncSessionLocal,
    poll_interval: float = 2.0,
    max_batches: int | None = None,
):
    semaphore = asyncio.Semaphore(concurrency)

    async def run_task(task_id):
        async with semaphore:
            await process_task(task_id, session_factory=session_factory)

    batches = 0
    while True:
        async with session_factory() as db:
            result = await db.execute(
                select(AudioTask.id)
                .where(AudioTask.status == "pending")
                .order_by(AudioTask.created_at)
                .limit(concurrency)
            )
            pending_ids = [row[0] for row in result.all()]

        if not pending_ids:
            if max_batches is not None:
                return
            await asyncio.sleep(poll_interval)
            continue

        batches += 1
        await asyncio.gather(*[run_task(tid) for tid in pending_ids])
        if max_batches is not None and batches >= max_batches:
            return


if __name__ == "__main__":
    asyncio.run(worker_loop())
