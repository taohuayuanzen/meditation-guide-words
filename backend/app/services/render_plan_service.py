import json
import logging
import re
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit, urlunsplit

import httpx
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.script import Script
from app.models.setting import Setting
from app.schemas.audio_render_plan import (
    AudioRenderPlan,
    DurationEstimate,
    RenderPlanPreviewResponse,
)
from app.schemas.script_plan import ScriptPlan
from app.services.audio_renderer import canonical_digest
from app.services.pause_profiles import get_pause_profile, pause_strategy, quantify_pause
from app.services.tts_capabilities import get_tts_capabilities

logger = logging.getLogger(__name__)

ALIYUN_VOICES = {
    "qwen-audio-3.0-tts-plus": ["longanlingxin", "longanlufeng"],
    "qwen-audio-3.0-tts-flash": [
        "longanfengyue",
        "longanyuanfei",
        "longanlingxi",
        "longanxiaoxin",
        "longanhuan_v3.6",
        "longjielidou_v3.6",
        "longpaopao_v3.6",
        "longhuohuo_v3.6",
        "longchuanshu_v3.6",
        "loongmary",
        "loongeva_v3.6",
        "loongjohn",
    ],
    "cosyvoice-v3-flash": ["longanyang", "longanhuan_v3"],
}

DifyCaller = Callable[[str, str, dict], Awaitable[dict]]


def _strip_json_fence(value: str) -> str:
    cleaned = value.strip()
    while re.match(r"^<think>\s*", cleaned, flags=re.I):
        closing_tag = re.search(r"</think>", cleaned, flags=re.I)
        if closing_tag is None:
            raise ValueError("App B 思考内容未完整结束")
        cleaned = cleaned[closing_tag.end() :].lstrip()
    return re.sub(r"\s*```$", "", re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)).strip()


async def call_dify_audio(base_url: str, api_key: str, payload: dict) -> dict:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/chat-messages", headers=headers, json=payload
            )
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ValueError(f"App B 调用失败: {exc}") from exc
    answer = body.get("answer")
    if not isinstance(answer, str):
        raise ValueError("App B 响应缺少 answer")
    try:
        parsed = json.loads(_strip_json_fence(answer))
    except json.JSONDecodeError as exc:
        raise ValueError("App B 未返回合法 JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("App B render_plan 必须是 JSON 对象")
    return parsed


async def _runtime_context(db: AsyncSession) -> tuple[dict, dict]:
    setting = (await db.execute(select(Setting).where(Setting.id == 1))).scalar_one_or_none()
    tts = dict(setting.tts_config) if setting else {}
    dify = dict(setting.dify_config) if setting else {}
    from app.config import settings

    dify["base_url"] = dify.get("base_url") or settings.dify_base_url
    dify["audio_app_key"] = dify.get("audio_app_key") or settings.dify_audio_app_key
    if not dify["audio_app_key"]:
        raise ValueError("Dify App B 未配置")
    provider = tts.get("provider", "volcano")
    model = tts.get("model", "qwen-audio-3.0-tts-plus")
    configured_voice = tts.get("voice_id", "")
    if provider == "aliyun":
        allowed = ALIYUN_VOICES.get(model)
        if not allowed:
            raise ValueError(f"不支持的 TTS 模型: {model}")
    else:
        if not configured_voice:
            raise ValueError("当前 TTS 配置缺少 voice_id")
        allowed = [configured_voice]
    default_voice = configured_voice if configured_voice in allowed else allowed[0]
    return dify, {
        "provider": provider,
        "model": model,
        "allowed_voices": allowed,
        "default_voice": default_voice,
        "configured_voice": configured_voice,
    }


def build_tts_snapshot(tts_config: dict, plan: AudioRenderPlan) -> dict:
    provider = tts_config.get("provider", "aliyun")
    model = tts_config.get("model", "qwen-audio-3.0-tts-plus")
    capabilities = get_tts_capabilities(provider, model, plan.voice.voice_id)
    parsed = urlsplit(tts_config.get("base_url", "https://dashscope.aliyuncs.com/api/v1"))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("TTS Base URL 无效")
    if parsed.username or parsed.password:
        raise ValueError("TTS Base URL 不得包含凭证")
    return {
        "provider": provider,
        "model": model,
        "voice_id": plan.voice.voice_id,
        "rate": plan.voice.rate,
        "volume": plan.voice.volume,
        "pitch": plan.voice.pitch,
        "instruction": plan.voice.instruction if capabilities.supports_instruction else None,
        "output_format": "mp3",
        "sample_rate": 48000,
        "base_url": urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", "")),
    }


def build_preview_digest(script: Script, plan_digest: str, tts_config: dict, snapshot: dict) -> str:
    safe_config = {
        "provider": tts_config.get("provider", "aliyun"),
        "model": tts_config.get("model", "qwen-audio-3.0-tts-plus"),
        "voice_id": tts_config.get("voice_id", ""),
        "speed": tts_config.get("speed", 1.0),
        "volume": tts_config.get("volume", 1.0),
        "output_format": tts_config.get("output_format", "mp3"),
    }
    return canonical_digest(
        {
            "script_id": script.id,
            "script_plan": script.script_plan,
            "script_updated_at": script.updated_at.isoformat() if script.updated_at else None,
            "render_plan_digest": plan_digest,
            "tts_config": safe_config,
            "tts_snapshot": snapshot,
        }
    )


def validate_render_plan(
    raw_plan: dict, script_plan: ScriptPlan, profile_id: str, tts_context: dict
) -> AudioRenderPlan:
    try:
        plan = AudioRenderPlan.model_validate(raw_plan)
    except ValidationError as exc:
        raise ValueError(f"App B render_plan 结构无效: {exc}") from exc
    if plan.pause_profile_id != profile_id:
        raise ValueError("App B 返回的停顿档案 ID 不匹配")
    if plan.voice.voice_id not in tts_context["allowed_voices"]:
        raise ValueError("App B 返回了不允许的 voice_id")
    if len(plan.segments) != len(script_plan.blocks):
        raise ValueError("render_plan segment 数量与 script_plan 不一致")
    profile = get_pause_profile(profile_id)
    for index, (segment, block) in enumerate(zip(plan.segments, script_plan.blocks, strict=True)):
        if segment.id != block.id or segment.text != block.text:
            raise ValueError(f"render_plan 第 {index + 1} 段改写了 ID、顺序或正文")
        if segment.pause_kind != block.pause_after.kind:
            raise ValueError(f"render_plan 第 {index + 1} 段 pause_kind 不匹配")
        expected_strategy = pause_strategy(block.pause_after.kind)
        if segment.pause_strategy != expected_strategy:
            raise ValueError(f"render_plan 第 {index + 1} 段 pause_strategy 不匹配")
        expected_ms = quantify_pause(block.pause_after, profile)
        if abs(segment.pause_after_ms - expected_ms) > 50:
            raise ValueError(f"render_plan 第 {index + 1} 段停顿时长与档案不一致")
        segment.pause_after_ms = expected_ms
    return plan


def estimate_duration(plan: AudioRenderPlan, script_plan: ScriptPlan) -> DurationEstimate:
    text = "".join(segment.text for segment in plan.segments)
    # zh_v1: 每秒 4 个可朗读字符；rate 越高，朗读越快。
    spoken_chars = len(re.sub(r"[\s，。！？；：、,.!?;:]", "", text))
    speech_ms = round(spoken_chars / (4.0 * plan.voice.rate) * 1000)
    semantic_natural_ms = sum(
        segment.pause_after_ms for segment in plan.segments if segment.pause_strategy == "natural"
    )
    punctuation_ms = (
        len(re.findall(r"[，、,:：]", text)) * 180 + len(re.findall(r"[。！？；.!?;]", text)) * 350
    )
    natural_ms = semantic_natural_ms + punctuation_ms
    deterministic_ms = sum(
        segment.pause_after_ms for segment in plan.segments if segment.pause_strategy == "silence"
    )
    total_ms = speech_ms + natural_ms + deterministic_ms
    target = script_plan.target_duration_seconds
    total_seconds = round(total_ms / 1000)
    return DurationEstimate(
        estimated_speech_seconds=round(speech_ms / 1000),
        estimated_natural_pause_seconds=round(natural_ms / 1000),
        deterministic_pause_seconds=round(deterministic_ms / 1000),
        estimated_total_seconds=total_seconds,
        target_duration_seconds=target,
        duration_delta_seconds=total_seconds - target,
    )


async def preview_render_plan(
    db: AsyncSession,
    script: Script,
    profile_id: str,
    voice_prompt: str,
    *,
    dify_caller: DifyCaller = call_dify_audio,
) -> RenderPlanPreviewResponse:
    if not script.script_plan:
        raise ValueError("旧格式脚本不支持可控留白，请重新生成结构化引导词")
    script_plan = ScriptPlan.model_validate(script.script_plan)
    profile = get_pause_profile(profile_id)
    dify, tts_context = await _runtime_context(db)
    payload = {
        "inputs": {
            "script_plan": json.dumps(script_plan.model_dump(), ensure_ascii=False),
            "pause_profile": json.dumps(profile.public_dict(), ensure_ascii=False),
            "voice_prompt": voice_prompt,
            "tts_context": json.dumps(tts_context, ensure_ascii=False),
        },
        "query": voice_prompt,
        "response_mode": "blocking",
        "conversation_id": "",
        "user": "local-user",
    }
    logger.info(
        "[RenderPlan] preview script_id=%s profile=%s blocks=%s voice_prompt_len=%s",
        script.id,
        profile_id,
        len(script_plan.blocks),
        len(voice_prompt),
    )
    raw_plan = await dify_caller(dify["base_url"], dify["audio_app_key"], payload)
    plan = validate_render_plan(raw_plan, script_plan, profile_id, tts_context)
    estimate = estimate_duration(plan, script_plan)
    if estimate.deterministic_pause_seconds > 7200:
        raise ValueError("确定性停顿总时长超过产品上限 7200 秒")
    if estimate.estimated_total_seconds > 7200:
        raise ValueError("预计总时长超过产品上限 7200 秒")
    setting = (await db.execute(select(Setting).where(Setting.id == 1))).scalar_one_or_none()
    tts_config = dict(setting.tts_config) if setting else {}
    plan_digest = canonical_digest(plan.model_dump(mode="json"))
    snapshot = build_tts_snapshot(tts_config, plan)
    return RenderPlanPreviewResponse(
        render_plan=plan,
        render_plan_digest=plan_digest,
        preview_digest=build_preview_digest(script, plan_digest, tts_config, snapshot),
        estimate=estimate,
    )
