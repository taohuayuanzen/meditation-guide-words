import logging
import re
from collections.abc import Mapping
from datetime import timedelta
from typing import Any

import httpx

from app.services.music_provider import MusicGenerationResult, MusicServiceError
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)

MINIMAX_MODEL = "music-3.0"
DEFAULT_BASE_URL = "https://api.minimaxi.com/v1"
GENERATION_TIMEOUT_SECONDS = 600.0


async def generate_music(
    config: Mapping[str, Any],
    prompt: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout: float = GENERATION_TIMEOUT_SECONDS,
) -> MusicGenerationResult:
    api_key = str(config.get("api_key") or "").strip()
    if not api_key:
        raise MusicServiceError("MUSIC_CONFIG_MISSING", "未配置 MiniMax API Key")
    prompt = prompt.strip()
    if not 1 <= len(prompt) <= 2000:
        raise MusicServiceError("MUSIC_REQUEST_INVALID", "音乐 Prompt 长度必须为 1～2000 个字符")

    base_url = str(config.get("base_url") or DEFAULT_BASE_URL).strip().rstrip("/")
    source_format = str(config.get("source_format") or "mp3").lower()
    if source_format not in {"mp3", "wav"}:
        raise MusicServiceError("MUSIC_REQUEST_INVALID", "MiniMax 音乐源格式仅支持 mp3 或 wav")
    url = f"{base_url}/music_generation"
    payload = {
        "model": MINIMAX_MODEL,
        "prompt": prompt,
        "stream": False,
        "output_format": "url",
        "audio_setting": {"sample_rate": 44100, "bitrate": 256000, "format": source_format},
        "aigc_watermark": False,
        "lyrics_optimizer": False,
        "is_instrumental": True,
    }
    logger.info(
        "[MusicMiniMax] generating model=%s prompt_len=%s endpoint_host=%s",
        MINIMAX_MODEL,
        len(prompt),
        httpx.URL(url).host,
    )
    try:
        async with httpx.AsyncClient(transport=transport, timeout=timeout) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise MusicServiceError("MUSIC_TIMEOUT", "MiniMax 音乐生成请求超时") from exc
    except httpx.RequestError as exc:
        raise MusicServiceError("MUSIC_NETWORK_ERROR", "无法连接 MiniMax 音乐生成服务") from exc

    if response.status_code >= 400:
        raise _normalize_error(response)
    try:
        body = response.json()
        base_resp = body["base_resp"]
        status_code = int(base_resp["status_code"])
    except (KeyError, TypeError, ValueError) as exc:
        raise MusicServiceError("MUSIC_RESPONSE_INVALID", "MiniMax 返回结构异常") from exc
    if status_code != 0:
        raise _normalize_error(response)

    try:
        data = body["data"]
        status = str(data["status"]).lower()
        audio_url = str(data["audio"])
        request_id = str(body["trace_id"])
        extra = body.get("extra_info") or data.get("extra_info") or {}
        duration_ms = int(extra["music_duration"])
        sample_rate = _optional_int(extra.get("music_sample_rate"))
        channels = _optional_int(extra.get("music_channel"))
    except (KeyError, TypeError, ValueError) as exc:
        raise MusicServiceError("MUSIC_RESPONSE_INVALID", "MiniMax 返回结构异常") from exc

    if status not in {"2", "success", "succeeded", "completed", "complete"}:
        raise MusicServiceError("MUSIC_PROVIDER_ERROR", "MiniMax 音乐生成未完成")
    try:
        parsed_url = httpx.URL(audio_url)
    except httpx.InvalidURL as exc:
        raise MusicServiceError("MUSIC_RESPONSE_INVALID", "MiniMax 返回的音频地址无效") from exc
    if parsed_url.scheme != "https" or not parsed_url.host or not request_id or duration_ms <= 0:
        raise MusicServiceError("MUSIC_RESPONSE_INVALID", "MiniMax 返回内容不完整")

    return MusicGenerationResult(
        request_id=request_id,
        audio_id=None,
        audio_url=audio_url,
        expires_at=utc_now() + timedelta(hours=24),
        duration_seconds=round(duration_ms / 1000),
        sample_rate=sample_rate,
        channels=channels,
        source_format=source_format,
        estimated_cost=None,
    )


def _optional_int(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    return int(value)


def _normalize_error(response: httpx.Response) -> MusicServiceError:
    code = ""
    message = ""
    try:
        body = response.json()
        if isinstance(body, dict):
            base_resp = body.get("base_resp") or {}
            code = str(base_resp.get("status_code") or body.get("error_code") or "")
            message = str(base_resp.get("status_msg") or body.get("error_message") or "")
    except ValueError:
        pass
    fingerprint = f"{code} {message}".lower()
    status = response.status_code
    if code == "1004" or status == 401 or any(
        word in fingerprint for word in ("invalid api", "unauthorized")
    ):
        return MusicServiceError("MUSIC_AUTH_FAILED", "MiniMax API Key 无效")
    if code == "1002" or status == 429:
        return MusicServiceError("MUSIC_RATE_LIMITED", "MiniMax 音乐生成服务限流")
    if code == "1008" or any(
        word in fingerprint for word in ("insufficient", "balance", "permission", "quota")
    ):
        return MusicServiceError("MUSIC_ACCESS_DENIED", "MiniMax 模型权限、余额或额度不足")
    if code in {"1026", "1027"} or any(
        word in fingerprint for word in ("audit", "sensitive", "content")
    ):
        return MusicServiceError("MUSIC_CONTENT_REJECTED", "音乐 Prompt 未通过内容审核")
    if code == "1001":
        return MusicServiceError("MUSIC_TIMEOUT", "MiniMax 音乐生成请求超时")
    if code == "2013":
        return MusicServiceError("MUSIC_REQUEST_INVALID", "MiniMax 音乐生成请求参数错误")
    if status == 200 and code and code != "0":
        detail = _safe_detail(code, message)
        return MusicServiceError(
            "MUSIC_PROVIDER_ERROR",
            f"MiniMax 音乐生成失败{f'（{detail}）' if detail else ''}",
        )
    if status >= 500:
        return MusicServiceError("MUSIC_PROVIDER_ERROR", "MiniMax 音乐生成服务暂时不可用")
    detail = _safe_detail(code, message)
    return MusicServiceError(
        "MUSIC_REQUEST_REJECTED",
        f"MiniMax 拒绝了音乐生成请求{f'（{detail}）' if detail else f'（HTTP {status}）'}",
    )


def _safe_detail(code: str, message: str) -> str:
    raw = ": ".join(part for part in (code.strip(), message.strip()) if part)
    raw = re.sub(r"(?i)bearer\s+\S+", "Bearer [redacted]", raw)
    raw = re.sub(r"(?i)(?:sk-|eyj)[a-z0-9._-]+", "[key redacted]", raw)
    raw = re.sub(r"https?://\S+", "[url redacted]", raw)
    return raw[:300]
