import os
from datetime import datetime
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.audio_task import AudioTask
from app.models.script import Script
from app.utils.file_utils import ensure_dir, get_script_output_dir, sanitize_filename

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]
ArtifactTypeFilter = Annotated[str | None, Query(pattern=r"^(audio|script)$")]


def _audio_dir() -> str:
    return os.path.abspath(settings.audio_output_dir)


def _script_dir() -> str:
    return os.path.abspath(get_script_output_dir(settings.audio_output_dir))


def _strip_extension(name: str, ext: str) -> str:
    if name.lower().endswith(ext.lower()):
        return name[: -len(ext)]
    return name


def _format_time(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


@router.get("")
async def list_artifacts(db: DbSession, type: ArtifactTypeFilter = None):
    artifacts = []

    # 音频产物：扫描磁盘并关联 audio_tasks
    if type is None or type == "audio":
        audio_dir = _audio_dir()
        tasks_result = await db.execute(select(AudioTask).where(AudioTask.file_path.is_not(None)))
        tasks = tasks_result.scalars().all()
        task_by_basename = {}
        for task in tasks:
            if task.file_path:
                task_by_basename[os.path.basename(task.file_path)] = task

        if os.path.isdir(audio_dir):
            for filename in sorted(os.listdir(audio_dir)):
                file_path = os.path.join(audio_dir, filename)
                if not os.path.isfile(file_path):
                    continue
                task = task_by_basename.get(filename)
                script_title = None
                created_at = None
                task_id = None
                if task:
                    task_id = task.id
                    created_at = _format_time(task.created_at)
                    # 关联引导词标题
                    script_result = await db.execute(
                        select(Script.title).where(Script.id == task.script_id)
                    )
                    script_title = script_result.scalar_one_or_none()
                artifacts.append(
                    {
                        "id": f"audio_{task_id or filename}",
                        "type": "audio",
                        "name": filename,
                        "script_title": script_title,
                        "created_at": created_at,
                        "task_id": task_id,
                    }
                )

    # 引导词产物：扫描磁盘并关联 scripts
    if type is None or type == "script":
        script_dir = _script_dir()
        scripts_result = await db.execute(select(Script))
        scripts = scripts_result.scalars().all()
        script_by_id = {script.id: script for script in scripts}

        if os.path.isdir(script_dir):
            for filename in sorted(os.listdir(script_dir)):
                if not filename.lower().endswith(".md"):
                    continue
                file_path = os.path.join(script_dir, filename)
                if not os.path.isfile(file_path):
                    continue
                # 文件名格式：{title}_{id}.md
                script_id = None
                script = None
                without_ext = _strip_extension(filename, ".md")
                if "_" in without_ext:
                    try:
                        script_id = int(without_ext.rsplit("_", 1)[-1])
                        script = script_by_id.get(script_id)
                    except ValueError:
                        pass
                title = script.title if script else without_ext
                created_at = _format_time(script.created_at) if script else None
                artifacts.append(
                    {
                        "id": f"script_{script_id or filename}",
                        "type": "script",
                        "name": filename,
                        "title": title,
                        "created_at": created_at,
                        "script_id": script_id,
                    }
                )

    return artifacts


@router.get("/{artifact_id}/download")
async def download_artifact(artifact_id: str, db: DbSession):
    artifact_type, _, raw_id = artifact_id.partition("_")
    if artifact_type not in ("audio", "script"):
        raise HTTPException(status_code=400, detail="Invalid artifact id")

    if artifact_type == "audio":
        try:
            task_id = int(raw_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid audio artifact id") from exc
        result = await db.execute(select(AudioTask).where(AudioTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task or not task.file_path or not os.path.exists(task.file_path):
            raise HTTPException(status_code=404, detail="Audio file not found")
        return FileResponse(
            task.file_path,
            filename=os.path.basename(task.file_path),
            media_type="application/octet-stream",
        )

    # script
    try:
        script_id = int(raw_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid script artifact id") from exc
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    content = f"""# {script.title}

创建时间：{script.created_at}
会话 ID：{script.session_id or "无"}

---

{script.content}
"""
    filename = f"{sanitize_filename(script.title)}_{script.id}.md"
    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


class RenamePayload(BaseModel):
    new_name: str


@router.post("/{artifact_id}/rename")
async def rename_artifact(artifact_id: str, payload: RenamePayload, db: DbSession):
    artifact_type, _, raw_id = artifact_id.partition("_")
    if artifact_type not in ("audio", "script"):
        raise HTTPException(status_code=400, detail="Invalid artifact id")

    new_name = sanitize_filename(payload.new_name)
    if not new_name:
        raise HTTPException(status_code=400, detail="Invalid name")

    if artifact_type == "audio":
        try:
            task_id = int(raw_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid audio artifact id") from exc
        result = await db.execute(select(AudioTask).where(AudioTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task or not task.file_path:
            raise HTTPException(status_code=404, detail="Audio task not found")
        if not os.path.exists(task.file_path):
            raise HTTPException(status_code=404, detail="Audio file missing")

        old_path = task.file_path
        ext = os.path.splitext(old_path)[1]
        new_filename = f"{new_name}{ext}"
        new_path = os.path.join(os.path.dirname(old_path), new_filename)

        if new_path != old_path and os.path.exists(new_path):
            raise HTTPException(status_code=409, detail="File already exists")

        os.rename(old_path, new_path)
        task.file_path = new_path
        await db.commit()
        await db.refresh(task)
        return {"id": artifact_id, "name": new_filename}

    # script
    try:
        script_id = int(raw_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid script artifact id") from exc
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    script_dir = _script_dir()
    old_filename = f"{sanitize_filename(script.title)}_{script.id}.md"
    old_path = os.path.join(script_dir, old_filename)
    new_filename = f"{new_name}_{script.id}.md"
    new_path = os.path.join(script_dir, new_filename)

    if new_path != old_path and os.path.exists(new_path):
        raise HTTPException(status_code=409, detail="File already exists")

    # 用新标题重新生成文件内容并写入新路径
    ensure_dir(script_dir)
    content = f"""# {new_name}

创建时间：{script.created_at}
会话 ID：{script.session_id or "无"}

---

{script.content}
"""
    with open(new_path, "w", encoding="utf-8") as f:
        f.write(content)

    # 删除旧文件（如果存在且路径不同）
    if os.path.exists(old_path) and old_path != new_path:
        os.remove(old_path)

    script.title = new_name
    await db.commit()
    await db.refresh(script)
    return {"id": artifact_id, "name": new_filename}


@router.delete("/{artifact_id}", status_code=204)
async def delete_artifact(artifact_id: str, db: DbSession):
    artifact_type, _, raw_id = artifact_id.partition("_")
    if artifact_type not in ("audio", "script"):
        raise HTTPException(status_code=400, detail="Invalid artifact id")

    if artifact_type == "audio":
        try:
            task_id = int(raw_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid audio artifact id") from exc
        result = await db.execute(select(AudioTask).where(AudioTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Audio task not found")
        if task.file_path and os.path.exists(task.file_path):
            os.remove(task.file_path)
        await db.delete(task)
        await db.commit()
        return

    # script
    try:
        script_id = int(raw_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid script artifact id") from exc
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    script_dir = _script_dir()
    old_filename = f"{sanitize_filename(script.title)}_{script.id}.md"
    old_path = os.path.join(script_dir, old_filename)
    if os.path.exists(old_path):
        os.remove(old_path)
    await db.delete(script)
    await db.commit()
