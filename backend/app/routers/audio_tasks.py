import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.audio_task import AudioTask
from app.schemas.audio_task import AudioTaskCreate, AudioTaskResponse

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
    task = AudioTask(
        script_id=payload.script_id,
        voice_prompt=payload.voice_prompt,
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
    await db.commit()
    await db.refresh(task)
    return task
