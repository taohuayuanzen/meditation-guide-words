import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.setting import Setting
from app.schemas.setting import LLMConfig, SettingSchema, TTSConfig

logger = logging.getLogger(__name__)

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def _get_or_create_setting(db: AsyncSession) -> Setting:
    result = await db.execute(select(Setting).where(Setting.id == 1))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = Setting(id=1)
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
    return setting


@router.get("", response_model=SettingSchema)
async def get_settings(db: DbSession):
    setting = await _get_or_create_setting(db)
    return SettingSchema(
        llm_config=setting.llm_config,
        tts_config=setting.tts_config,
        dify_config=setting.dify_config,
        general_config=setting.general_config,
    )


@router.post("", response_model=SettingSchema)
async def save_settings(payload: SettingSchema, db: DbSession):
    setting = await _get_or_create_setting(db)
    setting.llm_config = payload.llm_config.model_dump()
    setting.tts_config = payload.tts_config.model_dump()
    setting.dify_config = payload.dify_config.model_dump()
    setting.general_config = payload.general_config.model_dump()
    await db.commit()
    await db.refresh(setting)
    return payload


@router.post("/test-llm")
async def test_llm(config: LLMConfig):
    if not config.api_key or not config.base_url:
        raise HTTPException(status_code=400, detail="LLM API Key 或 Base URL 未配置")
    url = config.base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {config.api_key}"}
    payload = {
        "model": config.model or "deepseek-chat",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 5,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        logger.warning("LLM test failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"LLM 连接失败: {exc}") from exc
    if response.status_code >= 400:
        logger.warning("LLM test returned %s: %s", response.status_code, response.text[:200])
        raise HTTPException(status_code=502, detail=f"LLM 返回错误: HTTP {response.status_code}")
    return {"status": "ok"}


@router.post("/test-tts")
async def test_tts(config: TTSConfig):
    # TODO(T5): 接入 TTSService 真实合成验证；当前仅校验配置完整性
    if not config.api_key:
        raise HTTPException(status_code=400, detail="TTS API Key 未配置")
    return {"status": "ok"}
