import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.music_task import MusicTask
from app.models.setting import Setting
from app.schemas.music_task import (
    MusicCapabilitiesResponse,
    MusicDownloadItem,
    MusicDownloadsResponse,
    MusicTaskCreate,
    MusicTaskResponse,
    MusicTaskRetry,
)
from app.schemas.setting import MusicConfig
from app.services.media_capabilities import get_media_capabilities
from app.services.music_files import (
    delete_music_files,
    get_music_file,
    list_music_files,
)
from app.services.music_postprocessor import MusicProcessingError, probe_audio
from app.services.music_worker import url_is_expired

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def _get_task_or_404(db: AsyncSession, task_id: int) -> MusicTask:
    task = await db.get(MusicTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Music task not found")
    return task


@router.get("/capabilities", response_model=MusicCapabilitiesResponse)
async def capabilities():
    return get_media_capabilities().model_dump()


@router.post("", response_model=MusicTaskResponse, status_code=201)
async def create_task(payload: MusicTaskCreate, db: DbSession):
    setting = await db.get(Setting, 1)
    config = MusicConfig.model_validate((setting.music_config if setting else None) or {})
    provider_config = config.minimax if config.provider == "minimax" else config.aliyun
    if config.provider == "minimax" and not provider_config.api_key:
        raise HTTPException(status_code=400, detail="MiniMax API Key 未配置")
    if config.provider == "aliyun" and (
        not config.aliyun.api_key or not config.aliyun.workspace_id
    ):
        raise HTTPException(status_code=400, detail="音乐 API Key 或 Workspace ID 未配置")
    media = get_media_capabilities()
    if not media.music_processing_available:
        missing = []
        if not media.ffmpeg_available:
            missing.append("FFmpeg")
        if not media.ffprobe_available:
            missing.append("FFprobe")
        detail = f"音乐处理能力不可用：缺少 {'、'.join(missing)}"
        raise HTTPException(status_code=503, detail=detail)

    task = MusicTask(
        prompt=payload.prompt,
        effective_prompt=payload.effective_prompt,
        preset_params=payload.preset_params,
        provider=config.provider,
        model=provider_config.model,
        source_format=provider_config.source_format,
        status="pending",
        stage="generating",
        target_duration_seconds=payload.target_duration_seconds,
        output_format="mp3",
        is_ai_generated=True,
        watermark_enabled=False,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("", response_model=list[MusicTaskResponse])
async def list_tasks(db: DbSession):
    result = await db.execute(select(MusicTask).order_by(MusicTask.created_at.desc()))
    return result.scalars().all()


@router.get("/{task_id}", response_model=MusicTaskResponse)
async def get_task(task_id: int, db: DbSession):
    return await _get_task_or_404(db, task_id)


@router.get("/{task_id}/downloads", response_model=MusicDownloadsResponse)
async def downloads(task_id: int, db: DbSession):
    task = await _get_task_or_404(db, task_id)
    return MusicDownloadsResponse(
        items=[
            MusicDownloadItem(
                kind=item.kind,
                format=item.format,
                label=item.label,
                size=item.path.stat().st_size,
                duration_seconds=item.duration_seconds,
                download_url=f"/api/music-tasks/{task.id}/download/{item.kind}",
            )
            for item in list_music_files(task)
        ]
    )


@router.get("/{task_id}/download/{kind}")
async def download(task_id: int, kind: str, db: DbSession):
    if kind not in {"source", "final"}:
        raise HTTPException(status_code=400, detail="无效的音乐下载类型")
    task = await _get_task_or_404(db, task_id)
    item = get_music_file(task, kind)
    if item is None:
        raise HTTPException(status_code=404, detail="音乐文件不存在")
    media_type = "audio/wav" if item.format == "wav" else "audio/mpeg"
    return FileResponse(item.path, filename=item.path.name, media_type=media_type)


@router.post("/{task_id}/retry", response_model=MusicTaskResponse)
async def retry_task(
    task_id: int,
    db: DbSession,
    payload: MusicTaskRetry | None = None,
):
    task = await _get_task_or_404(db, task_id)
    final = get_music_file(task, "final")
    if final is not None:
        try:
            info = await asyncio.to_thread(probe_audio, final.path)
        except MusicProcessingError as exc:
            raise HTTPException(status_code=409, detail=exc.message) from exc
        if abs(info.duration_seconds - task.target_duration_seconds) > 1:
            raise HTTPException(status_code=409, detail="最终音乐时长校验失败")
        task.file_path = str(final.path)
        task.final_duration_seconds = round(info.duration_seconds)
        task.status = "completed"
        task.stage = "processing"
        task.error_code = None
        task.error_msg = None
        await db.commit()
        await db.refresh(task)
        return task

    source = get_music_file(task, "source")
    existing_wav = source.path if source else None
    if existing_wav is not None:
        task.source_file_path = str(existing_wav)
        task.status = "processing"
        task.stage = "source_ready"
        task.error_code = None
        task.error_msg = None
        await db.commit()
        await db.refresh(task)
        return task

    if task.status != "failed":
        raise HTTPException(status_code=409, detail="音乐任务仍在执行或等待执行")

    if task.remote_audio_url:
        if url_is_expired(task.remote_url_expires_at):
            raise HTTPException(
                status_code=409,
                detail="音乐下载地址已过期；为避免重复计费，请新建任务",
            )
        task.status = "pending"
        task.stage = "downloading"
        task.download_retry_count = 0
    elif task.request_id or task.remote_audio_id:
        raise HTTPException(
            status_code=409,
            detail="任务已有远端生成标识但缺少下载地址；为避免重复计费，不能重新生成",
        )
    else:
        if task.provider == "minimax" and not (payload and payload.confirm_regenerate):
            raise HTTPException(
                status_code=409,
                detail=(
                    "重新生成会再次调用 MiniMax，并可能重复计费；"
                    "请设置 confirm_regenerate=true 明确确认"
                ),
            )
        task.status = "pending"
        task.stage = "generating"
        task.retry_count = 0

    task.error_code = None
    task.error_msg = None
    task.completed_at = None
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, db: DbSession):
    task = await _get_task_or_404(db, task_id)
    if task.status == "processing":
        raise HTTPException(status_code=409, detail="音乐正在处理中，当前版本不支持取消")
    try:
        delete_music_files(task)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="音乐文件删除失败") from exc
    await db.delete(task)
    await db.commit()
