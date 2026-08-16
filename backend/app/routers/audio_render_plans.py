from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.script import Script
from app.schemas.audio_render_plan import RenderPlanPreviewRequest, RenderPlanPreviewResponse
from app.services.pause_profiles import PAUSE_PROFILES
from app.services.render_plan_service import preview_render_plan

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/pause-profiles")
async def list_pause_profiles():
    return {"items": [profile.public_dict() for profile in PAUSE_PROFILES.values()]}


@router.post("/preview", response_model=RenderPlanPreviewResponse)
async def preview(payload: RenderPlanPreviewRequest, db: DbSession):
    script = (
        await db.execute(select(Script).where(Script.id == payload.script_id))
    ).scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="Script not found")
    try:
        return await preview_render_plan(
            db, script, payload.pause_profile_id, payload.voice_prompt.strip()
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
