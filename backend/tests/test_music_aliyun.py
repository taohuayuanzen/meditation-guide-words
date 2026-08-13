import json
from datetime import UTC, datetime

import httpx
import pytest

from app.services.music_aliyun import MusicServiceError, generate_music


def _success_response() -> dict:
    return {
        "output": {
            "audio": {
                "id": "audio-1",
                "url": "https://oss.example/music.wav?signature=secret",
                "expires_at": 2_000_000_000,
            },
            "extra_info": {"channels": 2, "sample_rate": "48000"},
            "finish_reason": "stop",
        },
        "usage": {"duration": 200},
        "request_id": "request-1",
    }


async def test_builds_non_streaming_instrumental_wav_request():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        captured["json"] = json.loads(request.content)
        return httpx.Response(200, json=_success_response())

    result = await generate_music(
        {"api_key": "sk-secret", "workspace_id": "ws-123"},
        "安静的钢琴曲",
        transport=httpx.MockTransport(handler),
    )

    request = captured["request"]
    assert str(request.url).startswith(
        "https://ws-123.cn-beijing.maas.aliyuncs.com/api/v1/services/audio/music/generation"
    )
    assert request.headers["Authorization"] == "Bearer sk-secret"
    assert "X-DashScope-SSE" not in request.headers
    assert captured["json"] == {
        "model": "fun-music-v1",
        "input": {
            "prompt": "安静的钢琴曲",
            "is_instrumental": True,
            "format": "wav",
            "enable_aigc_watermark": False,
        },
    }
    assert result.request_id == "request-1"
    assert result.audio_id == "audio-1"
    assert result.duration_seconds == 200
    assert result.sample_rate == 48000
    assert result.channels == 2
    assert result.expires_at == datetime.fromtimestamp(2_000_000_000, tz=UTC)


@pytest.mark.parametrize(
    ("status", "body", "expected_code", "retryable"),
    [
        (401, {"code": "InvalidApiKey"}, "MUSIC_AUTH_FAILED", False),
        (403, {"code": "AccessDenied"}, "MUSIC_ACCESS_DENIED", False),
        (404, {}, "MUSIC_ENDPOINT_INVALID", False),
        (429, {}, "MUSIC_RATE_LIMITED", True),
        (400, {"code": "DataInspectionFailed"}, "MUSIC_CONTENT_REJECTED", False),
        (503, {}, "MUSIC_PROVIDER_ERROR", True),
    ],
)
async def test_standardizes_provider_errors(status, body, expected_code, retryable):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)

    with pytest.raises(MusicServiceError) as exc_info:
        await generate_music(
            {"api_key": "key", "workspace_id": "workspace"},
            "prompt",
            transport=httpx.MockTransport(handler),
        )
    assert exc_info.value.code == expected_code
    assert exc_info.value.retryable is retryable


async def test_timeout_is_retryable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    with pytest.raises(MusicServiceError) as exc_info:
        await generate_music(
            {"api_key": "key", "workspace_id": "workspace"},
            "prompt",
            transport=httpx.MockTransport(handler),
        )
    assert exc_info.value.code == "MUSIC_TIMEOUT"
    assert exc_info.value.retryable is True


async def test_generic_provider_error_keeps_safe_diagnostic_detail():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            400,
            json={
                "code": "InvalidParameter",
                "message": "bad value; key sk-never-show at https://example.com?a=secret",
            },
        )
    )
    with pytest.raises(MusicServiceError) as exc_info:
        await generate_music(
            {"api_key": "key", "workspace_id": "workspace"},
            "prompt",
            transport=transport,
        )
    assert exc_info.value.code == "MUSIC_REQUEST_REJECTED"
    assert "InvalidParameter" in exc_info.value.message
    assert "sk-never-show" not in exc_info.value.message
    assert "https://example.com" not in exc_info.value.message


async def test_rejects_invalid_response_structure():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"output": {}}))
    with pytest.raises(MusicServiceError) as exc_info:
        await generate_music(
            {"api_key": "key", "workspace_id": "workspace"},
            "prompt",
            transport=transport,
        )
    assert exc_info.value.code == "MUSIC_RESPONSE_INVALID"


async def test_logs_do_not_contain_key_or_signed_url(caplog):
    caplog.set_level("INFO")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=_success_response())
    )
    await generate_music(
        {"api_key": "sk-never-log", "workspace_id": "workspace"},
        "prompt",
        transport=transport,
    )
    assert "sk-never-log" not in caplog.text
    assert "signature=secret" not in caplog.text
