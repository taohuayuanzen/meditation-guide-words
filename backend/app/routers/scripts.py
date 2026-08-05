from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.script import Script
from app.schemas.script import ScriptCreate, ScriptListResponse, ScriptResponse

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]
Page = Annotated[int | None, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]


async def _get_script_or_404(db: AsyncSession, script_id: int) -> Script:
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.get("", response_model=ScriptListResponse)
async def list_scripts(db: DbSession, page: Page = None, page_size: PageSize = 20):
    total = (await db.execute(select(func.count(Script.id)))).scalar_one()
    query = select(Script).order_by(Script.created_at.desc())
    if page is not None:
        query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return ScriptListResponse(items=result.scalars().all(), total=total)


@router.post("", response_model=ScriptResponse, status_code=201)
async def create_script(payload: ScriptCreate, db: DbSession):
    script = Script(**payload.model_dump())
    db.add(script)
    await db.commit()
    await db.refresh(script)
    return script


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(script_id: int, db: DbSession):
    return await _get_script_or_404(db, script_id)


@router.put("/{script_id}", response_model=ScriptResponse)
async def update_script(script_id: int, payload: ScriptCreate, db: DbSession):
    script = await _get_script_or_404(db, script_id)
    for key, value in payload.model_dump().items():
        setattr(script, key, value)
    await db.commit()
    await db.refresh(script)
    return script


@router.delete("/{script_id}", status_code=204)
async def delete_script(script_id: int, db: DbSession):
    script = await _get_script_or_404(db, script_id)
    await db.delete(script)
    await db.commit()
