import json
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.setting import Setting

logger = logging.getLogger(__name__)

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_dify_config(db: AsyncSession) -> dict:
    result = await db.execute(select(Setting).where(Setting.id == 1))
    setting = result.scalar_one_or_none()
    if not setting or not setting.dify_config.get("script_app_key"):
        raise HTTPException(status_code=400, detail="Dify 配置未完成，请先在设置页配置")
    return setting.dify_config


async def stream_dify(request: Request, api_key: str, base_url: str) -> StreamingResponse:
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async def event_generator():
        timeout = httpx.Timeout(connect=15.0, read=None, write=30.0, pool=15.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    f"{base_url.rstrip('/')}/chat-messages",
                    headers=headers,
                    json=body,
                ) as response:
                    if response.status_code >= 400:
                        error_bytes = await response.aread()
                        error_text = error_bytes.decode("utf-8", errors="replace")[:500]
                        logger.warning("Dify returned %s: %s", response.status_code, error_text)
                        yield _error_event(response.status_code, error_text)
                        return
                    async for chunk in response.aiter_bytes():
                        yield chunk
        except httpx.HTTPError as exc:
            logger.error("Dify request failed: %s", exc)
            detail = f"Dify 连接失败: {exc}"
            yield _error_event(502, detail)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _error_event(status_code: int, detail: str) -> bytes:
    payload = json.dumps(
        {"event": "error", "status": status_code, "detail": detail},
        ensure_ascii=False,
    )
    return f"data: {payload}\n\n".encode()


@router.post("/script/chat")
async def chat_script(request: Request, db: DbSession):
    config = await get_dify_config(db)
    return await stream_dify(request, config["script_app_key"], config["base_url"])


@router.post("/audio/chat")
async def chat_audio(request: Request, db: DbSession):
    config = await get_dify_config(db)
    return await stream_dify(request, config["audio_app_key"], config["base_url"])
