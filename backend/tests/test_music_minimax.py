import json

import httpx
import pytest

from app.services.music_minimax import generate_music
from app.services.music_provider import MusicServiceError


def _success_body():
    return {
        "data": {"audio": "https://cdn.example/music.mp3?signature=secret", "status": 2},
        "trace_id": "trace-1",
        "extra_info": {
            "music_duration": 25364,
            "music_sample_rate": 44100,
            "music_channel": 2,
        },
        "base_resp": {"status_code": 0, "status_msg": "success"},
    }


@pytest.mark.parametrize("source_format", ["mp3", "wav"])
async def test_minimax_request_and_success_response(source_format):
    captured = {}

    def handler(request: httpx.Request):
        captured["request"] = request
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_success_body())

    result = await generate_music(
        {
            "api_key": "secret",
            "base_url": "https://api.minimaxi.com/v1",
            "source_format": source_format,
        },
        "创作适合纯音乐。安静、舒缓。",
        transport=httpx.MockTransport(handler),
    )

    request = captured["request"]
    body = captured["body"]
    assert str(request.url) == "https://api.minimaxi.com/v1/music_generation"
    assert request.headers["authorization"] == "Bearer secret"
    assert body == {
        "model": "music-3.0",
        "prompt": "创作适合纯音乐。安静、舒缓。",
        "stream": False,
        "output_format": "url",
        "audio_setting": {"sample_rate": 44100, "bitrate": 256000, "format": source_format},
        "aigc_watermark": False,
        "lyrics_optimizer": False,
        "is_instrumental": True,
    }
    assert "lyrics" not in body
    assert result.request_id == "trace-1"
    assert result.audio_id is None
    assert result.duration_seconds == 25
    assert result.sample_rate == 44100
    assert result.channels == 2
    assert result.source_format == source_format
    assert result.estimated_cost is None


@pytest.mark.parametrize("prompt", ["", "x" * 2001])
async def test_minimax_prompt_length_is_validated_without_http(prompt):
    with pytest.raises(MusicServiceError) as error:
        await generate_music({"api_key": "secret"}, prompt)
    assert error.value.code == "MUSIC_REQUEST_INVALID"


async def test_minimax_rejects_unsupported_source_format_without_http():
    with pytest.raises(MusicServiceError) as error:
        await generate_music({"api_key": "secret", "source_format": "flac"}, "prompt")
    assert error.value.code == "MUSIC_REQUEST_INVALID"


@pytest.mark.parametrize(
    ("status", "body", "code"),
    [
        (401, {}, "MUSIC_AUTH_FAILED"),
        (429, {}, "MUSIC_RATE_LIMITED"),
        (500, {}, "MUSIC_PROVIDER_ERROR"),
        (403, {"base_resp": {"status_msg": "insufficient balance"}}, "MUSIC_ACCESS_DENIED"),
        (400, {"base_resp": {"status_msg": "content audit failed"}}, "MUSIC_CONTENT_REJECTED"),
        (
            200,
            {"base_resp": {"status_code": 1000, "status_msg": "generation failed"}},
            "MUSIC_PROVIDER_ERROR",
        ),
        (200, {"base_resp": {"status_code": 1004}}, "MUSIC_AUTH_FAILED"),
        (200, {"base_resp": {"status_code": 1008}}, "MUSIC_ACCESS_DENIED"),
        (200, {"base_resp": {"status_code": 1026}}, "MUSIC_CONTENT_REJECTED"),
        (200, {"base_resp": {"status_code": 2013}}, "MUSIC_REQUEST_INVALID"),
    ],
)
async def test_minimax_http_errors_are_normalized(status, body, code):
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json=body))
    with pytest.raises(MusicServiceError) as error:
        await generate_music({"api_key": "secret"}, "prompt", transport=transport)
    assert error.value.code == code


async def test_minimax_invalid_response_hides_signed_url():
    body = _success_body()
    body["data"]["audio"] = "http://cdn.example/music.mp3?signature=never-expose"
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    with pytest.raises(MusicServiceError) as error:
        await generate_music({"api_key": "secret"}, "prompt", transport=transport)
    assert error.value.code == "MUSIC_RESPONSE_INVALID"
    assert "never-expose" not in error.value.message
