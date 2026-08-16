import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.audio_task import AudioTask
from app.models.script import Script
from app.models.setting import Setting
from app.schemas.audio_task import AudioTaskCreate, AudioTaskResponse
from app.schemas.script_plan import ScriptPlan
from app.services.audio_render_files import delete_audio_files
from app.services.audio_renderer import build_speech_segments, canonical_digest
from app.services.media_capabilities import get_media_capabilities
from app.services.render_plan_service import (
    ALIYUN_VOICES,
    build_preview_digest,
    build_tts_snapshot,
    estimate_duration,
    validate_render_plan,
)
from app.services.tts_capabilities import get_tts_capabilities, validate_snapshot_capabilities

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def _get_task_or_404(db: AsyncSession, task_id: int) -> AudioTask:
    result = await db.execute(select(AudioTask).where(AudioTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("", response_model=AudioTaskResponse, status_code=201)
async def create_task(payload: AudioTaskCreate, db: DbSession):
    script = (
        await db.execute(select(Script).where(Script.id == payload.script_id))
    ).scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="Script not found")
    # Historical plain-text scripts retain the legacy creation path. Structured scripts are
    # always immutable render-plan tasks.
    if script.script_plan:
        if (
            payload.render_plan is None
            or not payload.render_plan_digest
            or not payload.preview_digest
        ):
            raise HTTPException(
                status_code=422,
                detail="结构化脚本必须提供 render_plan、render_plan_digest 和 preview_digest",
            )
        setting = (await db.execute(select(Setting).where(Setting.id == 1))).scalar_one_or_none()
        tts_config = (setting.tts_config if setting else {}) or {}
        provider = tts_config.get("provider", "aliyun")
        model = tts_config.get("model", "qwen-audio-3.0-tts-plus")
        allowed = (
            ALIYUN_VOICES.get(model, [])
            if provider == "aliyun"
            else [tts_config.get("voice_id", "")]
        )
        try:
            plan = validate_render_plan(
                payload.render_plan.model_dump(),
                ScriptPlan.model_validate(script.script_plan),
                payload.render_plan.pause_profile_id,
                {"allowed_voices": [voice for voice in allowed if voice]},
            )
            plan_data = plan.model_dump(mode="json")
            digest = canonical_digest(plan_data)
            if digest != payload.render_plan_digest:
                raise ValueError("render_plan_digest 不匹配，请重新生成预览")
            snapshot = build_tts_snapshot(tts_config, plan)
            validate_snapshot_capabilities(snapshot)
            expected_preview_digest = build_preview_digest(script, digest, tts_config, snapshot)
            if expected_preview_digest != payload.preview_digest:
                raise ValueError("预览已过期：脚本或 TTS 配置已变化，请重新生成预览")
            capabilities = get_tts_capabilities(provider, model, plan.voice.voice_id)
            segments = build_speech_segments(plan_data, capabilities)
            estimate = estimate_duration(plan, ScriptPlan.model_validate(script.script_plan))
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        capabilities = get_media_capabilities()
        if not capabilities.ffmpeg_available or not capabilities.ffprobe_available:
            raise HTTPException(status_code=503, detail="FFmpeg/FFprobe 不可用")
        task = AudioTask(
            script_id=payload.script_id,
            voice_prompt=payload.voice_prompt,
            tts_params=payload.tts_params,
            render_plan=plan_data,
            render_plan_version=plan.version,
            render_plan_digest=digest,
            pause_profile_id=plan.pause_profile_id,
            tts_snapshot=snapshot,
            tts_snapshot_digest=canonical_digest(snapshot),
            estimated_speech_seconds=estimate.estimated_speech_seconds,
            estimated_pause_seconds=(
                estimate.estimated_natural_pause_seconds + estimate.deterministic_pause_seconds
            ),
            estimated_total_seconds=estimate.estimated_total_seconds,
            stage="plan_validated",
            completed_segments=0,
            total_segments=len(segments),
            status="pending",
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task
    task = AudioTask(
        script_id=payload.script_id,
        voice_prompt=payload.voice_prompt,
        tts_params=payload.tts_params,
        status="pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("", response_model=list[AudioTaskResponse])
async def list_tasks(db: DbSession):
    result = await db.execute(select(AudioTask).order_by(AudioTask.created_at.desc()))
    return result.scalars().all()


@router.get("/capabilities")
async def audio_capabilities():
    media = get_media_capabilities()
    return {
        "ffmpeg_available": media.ffmpeg_available,
        "ffprobe_available": media.ffprobe_available,
        "audio_rendering_available": media.ffmpeg_available and media.ffprobe_available,
    }


@router.get("/{task_id}", response_model=AudioTaskResponse)
async def get_task(task_id: int, db: DbSession):
    return await _get_task_or_404(db, task_id)


@router.get("/{task_id}/download")
async def download_task(task_id: int, db: DbSession):
    task = await _get_task_or_404(db, task_id)
    if task.status != "completed" or not task.file_path:
        raise HTTPException(status_code=404, detail="Audio not ready")
    if not os.path.exists(task.file_path):
        raise HTTPException(status_code=404, detail="Audio file missing")
    return FileResponse(task.file_path)


@router.post("/{task_id}/retry", response_model=AudioTaskResponse)
async def retry_task(task_id: int, db: DbSession):
    task = await _get_task_or_404(db, task_id)
    task.status = "pending"
    task.error_msg = None
    task.completed_at = None
    if task.render_plan is None:
        task.file_path = None
    task.retry_count = 0
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, db: DbSession):
    task = await _get_task_or_404(db, task_id)
    output_dir = None
    setting = (await db.execute(select(Setting).where(Setting.id == 1))).scalar_one_or_none()
    if setting and setting.general_config:
        output_dir = setting.general_config.get("audio_output_dir")
    delete_audio_files(task.id, output_dir)
    await db.delete(task)
    await db.commit()
