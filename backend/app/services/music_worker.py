import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings, setup_logging
from app.db import AsyncSessionLocal
from app.models.music_task import MusicTask
from app.models.setting import Setting
from app.schemas.setting import MusicConfig
from app.services.media_capabilities import get_media_capabilities
from app.services.music_aliyun import estimate_cost
from app.services.music_postprocessor import (
    AudioInfo,
    MusicProcessingError,
    probe_audio,
    process_music,
)
from app.services.music_provider import MusicGenerationResult, MusicServiceError, generate_music
from app.utils.time_utils import utc_now

setup_logging()
logger = logging.getLogger(__name__)

MAX_GENERATION_RETRIES = 1
MAX_DOWNLOAD_RETRIES = 2
DEFAULT_SOURCE_DIR = Path(settings.music_source_dir)
DEFAULT_FINAL_DIR = Path(settings.music_final_dir)

GenerateFunction = Callable[..., Awaitable[MusicGenerationResult]]
PostprocessFunction = Callable[[str | Path, str | Path, int], tuple[AudioInfo, AudioInfo]]
ProbeFunction = Callable[[str | Path], AudioInfo]


async def process_task(
    task_id: int,
    *,
    session_factory: async_sessionmaker = AsyncSessionLocal,
    source_dir: str | Path = DEFAULT_SOURCE_DIR,
    final_dir: str | Path = DEFAULT_FINAL_DIR,
    generate: GenerateFunction = generate_music,
    postprocess: PostprocessFunction = process_music,
    probe: ProbeFunction = probe_audio,
    download_transport: httpx.AsyncBaseTransport | None = None,
) -> None:
    async with session_factory() as db:
        task = await db.get(MusicTask, task_id)
        if task is None:
            return

        supported = {
            ("aliyun", "fun-music-v1", "wav"),
            ("minimax", "music-3.0", "mp3"),
        }
        if (task.provider, task.model, task.source_format) not in supported:
            await _mark_failed(
                db,
                task,
                "MUSIC_PROVIDER_UNSUPPORTED",
                f"不支持的音乐任务快照：{task.provider}/{task.model}/{task.source_format}",
            )
            return

        source_path = Path(source_dir) / f"{task.id}.{task.source_format}"
        final_path = Path(final_dir) / (
            f"{task.id}_{task.target_duration_seconds // 60}min.mp3"
        )

        existing_final = _existing_path(task.file_path, final_path, Path(final_dir))
        if existing_final is not None:
            try:
                final_info = await asyncio.to_thread(probe, existing_final)
            except MusicProcessingError:
                existing_final.unlink(missing_ok=True)
            else:
                if abs(final_info.duration_seconds - task.target_duration_seconds) <= 1:
                    await _mark_completed(db, task, existing_final, final_info)
                    return
                existing_final.unlink(missing_ok=True)

        existing_source = _existing_path(task.source_file_path, source_path, Path(source_dir))
        if existing_source is not None:
            task.source_file_path = str(existing_source)
            await _run_postprocessing(db, task, existing_source, final_path, postprocess)
            return

        task.status = "processing"
        task.completed_at = None
        await db.commit()

        if task.remote_audio_url:
            downloaded = await _resume_download(
                db,
                task,
                source_path,
                download_transport=download_transport,
            )
            if downloaded is not None:
                await _run_postprocessing(db, task, downloaded, final_path, postprocess)
            return

        if task.request_id or task.remote_audio_id:
            await _mark_failed(
                db,
                task,
                "MUSIC_RESPONSE_INVALID",
                "任务已有远端生成标识但缺少下载地址；为避免重复计费，不能重新生成",
            )
            return

        await _run_generation(db, task, generate)
        if not task.remote_audio_url:
            return
        downloaded = await _resume_download(
            db,
            task,
            source_path,
            download_transport=download_transport,
        )
        if downloaded is not None:
            await _run_postprocessing(db, task, downloaded, final_path, postprocess)


def _existing_path(
    saved_path: str | None,
    canonical_path: Path,
    controlled_root: Path,
) -> Path | None:
    root = controlled_root.resolve()
    for path in (canonical_path, Path(saved_path) if saved_path else None):
        if path is None:
            continue
        resolved = path.resolve()
        if resolved.is_relative_to(root) and _is_complete_file(resolved):
            return resolved
    return None


async def _run_generation(
    db: AsyncSession,
    task: MusicTask,
    generate: GenerateFunction,
) -> None:
    task.stage = "generating"
    await db.commit()

    setting = await db.get(Setting, 1)
    config = MusicConfig.model_validate(
        (setting.music_config if setting else None) or {}
    ).model_dump()
    provider_config = config.get(task.provider)
    if not isinstance(provider_config, dict):
        await _mark_failed(
            db,
            task,
            "MUSIC_CONFIG_MISSING",
            f"缺少 {task.provider} 音乐供应商配置",
        )
        return
    try:
        if generate is generate_music:
            result = await generate(
                task.provider, task.model, provider_config, task.effective_prompt
            )
        else:
            # Keep the injection seam used by the existing worker unit tests.
            result = await generate(provider_config, task.effective_prompt)
    except MusicServiceError as exc:
        await _handle_generation_failure(db, task, exc)
        return
    except Exception:
        logger.exception("[MusicWorker] task=%s unexpected generation failure", task.id)
        await _handle_generation_failure(
            db,
            task,
            MusicServiceError("MUSIC_INTERNAL_ERROR", "音乐生成发生内部错误"),
        )
        return

    task.request_id = result.request_id
    task.remote_audio_id = result.audio_id
    task.remote_audio_url = result.audio_url
    task.remote_url_expires_at = result.expires_at
    task.source_duration_seconds = result.duration_seconds
    task.sample_rate = result.sample_rate
    task.channels = result.channels
    task.estimated_cost = (
        estimate_cost(result.duration_seconds)
        if task.provider == "aliyun" and result.estimated_cost is None
        else result.estimated_cost
    )
    task.stage = "downloading"
    task.error_code = None
    task.error_msg = None
    await db.commit()
    logger.info(
        "[MusicWorker] task=%s generation persisted request_id=%s duration=%s",
        task.id,
        result.request_id,
        result.duration_seconds,
    )


async def _handle_generation_failure(
    db: AsyncSession,
    task: MusicTask,
    error: MusicServiceError,
) -> None:
    task.error_code = error.code
    task.error_msg = error.message
    if (
        task.provider == "aliyun"
        and error.retryable
        and task.retry_count < MAX_GENERATION_RETRIES
    ):
        task.retry_count += 1
        task.status = "pending"
    else:
        task.status = "failed"
        if task.provider == "minimax":
            task.error_msg = f"{error.message}；未自动重试，以避免重复计费"
    await db.commit()


async def _resume_download(
    db: AsyncSession,
    task: MusicTask,
    final_path: Path,
    *,
    download_transport: httpx.AsyncBaseTransport | None,
) -> Path | None:
    if _is_complete_file(final_path):
        await _mark_source_ready(db, task, final_path)
        return final_path
    if not task.remote_audio_url:
        await _mark_failed(db, task, "MUSIC_RESPONSE_INVALID", "任务缺少音乐下载地址")
        return None
    if url_is_expired(task.remote_url_expires_at):
        await _mark_failed(db, task, "MUSIC_URL_EXPIRED", "音乐下载地址已过期，请新建任务")
        return None

    task.stage = "downloading"
    await db.commit()
    part_path = final_path.with_suffix(f".{task.source_format}.part")
    try:
        final_path.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(
            transport=download_transport, timeout=300.0, follow_redirects=True
        ) as client:
            async with client.stream("GET", task.remote_audio_url) as response:
                response.raise_for_status()
                bytes_written = 0
                with part_path.open("wb") as output:
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            output.write(chunk)
                            bytes_written += len(chunk)
        if bytes_written <= 0:
            raise MusicServiceError("MUSIC_DOWNLOAD_EMPTY", "下载到的音乐文件为空")
        os.replace(part_path, final_path)
    except (httpx.HTTPError, OSError, MusicServiceError) as exc:
        part_path.unlink(missing_ok=True)
        await _handle_download_failure(db, task, exc)
        return None

    await _mark_source_ready(db, task, final_path)
    return final_path


async def _run_postprocessing(
    db: AsyncSession,
    task: MusicTask,
    source_path: Path,
    final_path: Path,
    postprocess: PostprocessFunction,
) -> None:
    task.source_file_path = str(source_path)
    task.status = "processing"
    task.stage = "processing"
    task.error_code = None
    task.error_msg = None
    await db.commit()
    try:
        source_info, final_info = await asyncio.to_thread(
            postprocess,
            source_path,
            final_path,
            task.target_duration_seconds,
        )
    except MusicProcessingError as exc:
        await _mark_failed(db, task, exc.code, exc.message)
        return
    except Exception:
        logger.exception("[MusicWorker] task=%s unexpected postprocessing failure", task.id)
        await _mark_failed(db, task, "MUSIC_PROCESSING_FAILED", "音乐时长处理发生内部错误")
        return

    task.source_duration_seconds = round(source_info.duration_seconds)
    task.sample_rate = source_info.sample_rate
    task.channels = source_info.channels
    await _mark_completed(db, task, final_path, final_info)


async def _mark_completed(
    db: AsyncSession,
    task: MusicTask,
    path: Path,
    info: AudioInfo,
) -> None:
    task.file_path = str(path)
    task.final_duration_seconds = round(info.duration_seconds)
    task.status = "completed"
    task.stage = "processing"
    task.error_code = None
    task.error_msg = None
    task.completed_at = utc_now()
    await db.commit()


async def _handle_download_failure(
    db: AsyncSession,
    task: MusicTask,
    error: Exception,
) -> None:
    if url_is_expired(task.remote_url_expires_at):
        await _mark_failed(db, task, "MUSIC_URL_EXPIRED", "音乐下载地址已过期，请新建任务")
        return
    code = error.code if isinstance(error, MusicServiceError) else "MUSIC_DOWNLOAD_FAILED"
    message = error.message if isinstance(error, MusicServiceError) else "原始音乐下载失败"
    task.error_code = code
    task.error_msg = message
    if task.download_retry_count < MAX_DOWNLOAD_RETRIES:
        task.download_retry_count += 1
        task.status = "pending"
    else:
        task.status = "failed"
    await db.commit()


async def _mark_source_ready(db: AsyncSession, task: MusicTask, path: Path) -> None:
    task.source_file_path = str(path)
    task.status = "processing"
    task.stage = "source_ready"
    task.error_code = None
    task.error_msg = None
    await db.commit()


async def _mark_failed(
    db: AsyncSession,
    task: MusicTask,
    code: str,
    message: str,
) -> None:
    task.status = "failed"
    task.error_code = code
    task.error_msg = message
    await db.commit()


def _is_complete_file(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def url_is_expired(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= utc_now()


async def worker_loop(
    concurrency: int = 1,
    *,
    session_factory: async_sessionmaker = AsyncSessionLocal,
    source_dir: str | Path = DEFAULT_SOURCE_DIR,
    final_dir: str | Path = DEFAULT_FINAL_DIR,
    poll_interval: float = 2.0,
    max_batches: int | None = None,
) -> None:
    semaphore = asyncio.Semaphore(concurrency)

    async def run_task(task_id: int) -> None:
        async with semaphore:
            await process_task(
                task_id,
                session_factory=session_factory,
                source_dir=source_dir,
                final_dir=final_dir,
            )

    batches = 0
    while True:
        async with session_factory() as db:
            result = await db.execute(
                select(MusicTask.id)
                .where(
                    or_(
                        MusicTask.status == "pending",
                        (MusicTask.status == "processing")
                        & (
                            MusicTask.stage.in_(
                                ["generating", "downloading", "source_ready", "processing"]
                            )
                        ),
                    )
                )
                .order_by(MusicTask.created_at)
                .limit(concurrency)
            )
            task_ids = [row[0] for row in result.all()]

        if not task_ids:
            if max_batches is not None:
                return
            await asyncio.sleep(poll_interval)
            continue

        batches += 1
        await asyncio.gather(*(run_task(task_id) for task_id in task_ids))
        if max_batches is not None and batches >= max_batches:
            return


async def _configured_worker() -> None:
    capabilities = get_media_capabilities()
    if not capabilities.music_processing_available:
        logger.error("[MusicWorker] FFmpeg/FFprobe unavailable; worker will not start")
        return
    async with AsyncSessionLocal() as db:
        setting = await db.get(Setting, 1)
        config = MusicConfig.model_validate((setting.music_config if setting else None) or {})
    await worker_loop(concurrency=config.worker_concurrency)


if __name__ == "__main__":
    asyncio.run(_configured_worker())
