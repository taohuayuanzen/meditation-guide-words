import logging
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import httpx

from app.services.music_provider import MusicGenerationResult, MusicServiceError

logger = logging.getLogger(__name__)

FUN_MUSIC_MODEL = "fun-music-v1"
FUN_MUSIC_PRICE_CNY_PER_SECOND = 0.002
GENERATION_TIMEOUT_SECONDS = 600.0


def resolve_base_url(config: Mapping[str, Any]) -> str:
    base_url = str(config.get("base_url") or "").strip().rstrip("/")
    if base_url:
        return base_url
    workspace_id = str(config.get("workspace_id") or "").strip()
    if not workspace_id:
        raise MusicServiceError("MUSIC_CONFIG_MISSING", "未配置音乐 Workspace ID")
    return f"https://{workspace_id}.cn-beijing.maas.aliyuncs.com/api/v1"


async def generate_music(
    config: Mapping[str, Any],
    prompt: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout: float = GENERATION_TIMEOUT_SECONDS,
) -> MusicGenerationResult:
    api_key = str(config.get("api_key") or "").strip()
    workspace_id = str(config.get("workspace_id") or "").strip()
    if not api_key or not workspace_id:
        raise MusicServiceError(
            "MUSIC_CONFIG_MISSING", "音乐 API Key 或 Workspace ID 未配置"
        )

    base_url = resolve_base_url(config)
    url = f"{base_url}/services/audio/music/generation"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": FUN_MUSIC_MODEL,
        "input": {
            "prompt": prompt,
            "is_instrumental": True,
            "format": "wav",
            "enable_aigc_watermark": False,
        },
    }
    logger.info(
        "[MusicAliyun] generating model=%s prompt_len=%s endpoint_host=%s",
        FUN_MUSIC_MODEL,
        len(prompt),
        httpx.URL(url).host,
    )
    try:
        async with httpx.AsyncClient(transport=transport, timeout=timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException as exc:
        raise MusicServiceError(
            "MUSIC_TIMEOUT", "音乐生成请求超时", retryable=True
        ) from exc
    except httpx.RequestError as exc:
        raise MusicServiceError(
            "MUSIC_NETWORK_ERROR", "无法连接音乐生成服务", retryable=True
        ) from exc

    if response.status_code >= 400:
        raise _normalize_http_error(response)

    try:
        data = response.json()
        output = data["output"]
        audio = output["audio"]
        extra_info = output.get("extra_info") or {}
        request_id = str(data["request_id"])
        audio_id = str(audio["id"])
        audio_url = str(audio["url"])
        expires_at_raw = int(audio["expires_at"])
        duration = int(data["usage"]["duration"])
        finish_reason = output.get("finish_reason")
        channels = _optional_int(extra_info.get("channels"))
        sample_rate = _optional_int(extra_info.get("sample_rate"))
    except (KeyError, TypeError, ValueError) as exc:
        raise MusicServiceError(
            "MUSIC_RESPONSE_INVALID", "音乐生成服务返回结构异常"
        ) from exc

    if not request_id or not audio_id or not audio_url or duration <= 0:
        raise MusicServiceError("MUSIC_RESPONSE_INVALID", "音乐生成服务返回内容不完整")
    if finish_reason not in {None, "stop"}:
        raise MusicServiceError("MUSIC_RESPONSE_INVALID", "音乐生成未正常结束")

    return MusicGenerationResult(
        request_id=request_id,
        audio_id=audio_id,
        audio_url=audio_url,
        expires_at=datetime.fromtimestamp(expires_at_raw, tz=UTC),
        channels=channels,
        sample_rate=sample_rate,
        duration_seconds=duration,
        source_format="wav",
        estimated_cost=estimate_cost(duration),
    )


def estimate_cost(duration_seconds: int) -> float:
    return round(duration_seconds * FUN_MUSIC_PRICE_CNY_PER_SECOND, 4)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _normalize_http_error(response: httpx.Response) -> MusicServiceError:
    provider_code = ""
    provider_message = ""
    try:
        body = response.json()
        if isinstance(body, dict):
            provider_code = str(body.get("code") or "")
            provider_message = str(body.get("message") or "")
    except ValueError:
        pass

    fingerprint = f"{provider_code} {provider_message}".lower()
    status = response.status_code
    if status in {401} or any(word in fingerprint for word in ("invalidapikey", "api key")):
        return MusicServiceError("MUSIC_AUTH_FAILED", "音乐 API Key 无效")
    if status == 429:
        return MusicServiceError("MUSIC_RATE_LIMITED", "音乐生成服务限流", retryable=True)
    if any(
        word in fingerprint
        for word in ("datainspection", "inappropriate", "sensitive", "content audit")
    ):
        return MusicServiceError("MUSIC_CONTENT_REJECTED", "音乐 Prompt 未通过内容审核")
    if status == 403:
        return MusicServiceError(
            "MUSIC_ACCESS_DENIED", "无权使用 fun-music-v1，请检查邀测权限和业务空间"
        )
    if status == 404:
        return MusicServiceError(
            "MUSIC_ENDPOINT_INVALID", "音乐服务地址或 Workspace ID 不正确"
        )
    if status >= 500:
        return MusicServiceError(
            "MUSIC_PROVIDER_ERROR", "音乐生成服务暂时不可用", retryable=True
        )
    detail = _safe_provider_error_detail(provider_code, provider_message)
    message = "音乐生成请求被服务端拒绝"
    if detail:
        message = f"{message}（{detail}）"
    else:
        message = f"{message}（HTTP {status}）"
    return MusicServiceError("MUSIC_REQUEST_REJECTED", message)


def _safe_provider_error_detail(code: str, message: str) -> str:
    raw = ": ".join(part for part in (code.strip(), message.strip()) if part)
    if not raw:
        return ""
    raw = re.sub(r"(?i)bearer\s+\S+", "Bearer [redacted]", raw)
    raw = re.sub(r"(?i)sk-[a-z0-9_-]+", "sk-[redacted]", raw)
    raw = re.sub(r"https?://\S+", "[url redacted]", raw)
    return raw[:300]
