import json
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.setting import Setting

logger = logging.getLogger(__name__)

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]


def _mask_key(key: str) -> str:
    """对 API Key 做脱敏展示，保留首尾各 4 位。"""
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


async def get_dify_config(db: AsyncSession, app_key_name: str) -> dict:
    """获取生效的 Dify 配置。

    优先级：
    1. 数据库 settings.dify_config（设置页保存的值）
    2. 环境变量 / .env 中的默认值
    """
    result = await db.execute(select(Setting).where(Setting.id == 1))
    db_setting = result.scalar_one_or_none()

    db_config = db_setting.dify_config if db_setting else {}
    db_base_url = db_config.get("base_url", "")
    db_script_key = db_config.get("script_app_key", "")
    db_audio_key = db_config.get("audio_app_key", "")

    env_base_url = settings.dify_base_url
    env_script_key = settings.dify_script_app_key
    env_audio_key = settings.dify_audio_app_key

    base_url = db_base_url or env_base_url
    script_app_key = db_script_key or env_script_key
    audio_app_key = db_audio_key or env_audio_key

    logger.debug(
        "[DifyConfig] resolved base_url=%s db_script=%s env_script=%s "
        "db_audio=%s env_audio=%s",
        base_url,
        bool(db_script_key),
        bool(env_script_key),
        bool(db_audio_key),
        bool(env_audio_key),
    )

    required_key = script_app_key if app_key_name == "script_app_key" else audio_app_key
    if not required_key:
        raise HTTPException(
            status_code=400,
            detail=(
                "Dify 配置未完成：请在设置页填写 App Key，"
                "或在 backend/.env 中配置 DIFY_SCRIPT_APP_KEY / DIFY_AUDIO_APP_KEY"
            ),
        )

    return {
        "base_url": base_url,
        "script_app_key": script_app_key,
        "audio_app_key": audio_app_key,
    }


async def stream_dify(
    request: Request,
    api_key: str,
    base_url: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> StreamingResponse:
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    logger.info(
        "[DifyProxy] request to %s/chat-messages, response_mode=%s, query_len=%s, inputs_keys=%s",
        base_url.rstrip("/"),
        body.get("response_mode"),
        len(body.get("query", "")),
        list(body.get("inputs", {}).keys()),
    )

    async def event_generator():
        timeout = httpx.Timeout(connect=15.0, read=None, write=30.0, pool=15.0)
        try:
            async with httpx.AsyncClient(transport=transport, timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    f"{base_url.rstrip('/')}/chat-messages",
                    headers=headers,
                    json=body,
                ) as response:
                    logger.debug(
                        "[DifyProxy] response status=%s headers=%s",
                        response.status_code,
                        dict(response.headers),
                    )
                    if response.status_code >= 400:
                        error_bytes = await response.aread()
                        error_text = error_bytes.decode("utf-8", errors="replace")[:500]
                        logger.warning(
                            "[DifyProxy] Dify returned error: status=%s body=%s",
                            response.status_code,
                            error_text,
                        )
                        yield _error_event(response.status_code, error_text)
                        return
                    async for chunk in response.aiter_bytes():
                        yield chunk
        except httpx.HTTPError as exc:
            logger.error("[DifyProxy] Dify request failed: %s", exc)
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
    config = await get_dify_config(db, "script_app_key")
    logger.info("[DifyProxy] script/chat using key=%s", _mask_key(config["script_app_key"]))
    return await stream_dify(request, config["script_app_key"], config["base_url"])


@router.post("/audio/chat")
async def chat_audio(request: Request, db: DbSession):
    config = await get_dify_config(db, "audio_app_key")
    logger.info("[DifyProxy] audio/chat using key=%s", _mask_key(config["audio_app_key"]))
    return await stream_dify(request, config["audio_app_key"], config["base_url"])
