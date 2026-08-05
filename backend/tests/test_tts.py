import base64
import json

import httpx
import pytest

from app.services.tts_aliyun import AliyunTTS
from app.services.tts_factory import get_tts_service
from app.services.tts_volcano import VolcanoTTS


def _volcano_ok_handler(tts_body):
    token_payload = {
        "code": 3000,
        "message": "Success",
        "data": {"token": "test-token", "expire_time": 604800},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/token"):
            return httpx.Response(200, json=token_payload)
        tts_body.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "code": 3000,
                "message": "Success",
                "data": [
                    {"data": base64.b64encode(b"part-1").decode(), "index": 0, "type": "binary"},
                    {"data": base64.b64encode(b"-part-2").decode(), "index": 1, "type": "binary"},
                ],
            },
        )

    return handler


def test_factory_volcano():
    service = get_tts_service(
        {"provider": "volcano", "api_key": "k", "secret_key": "s", "appid": "a"}
    )
    assert isinstance(service, VolcanoTTS)
    assert service.is_available()


def test_factory_aliyun():
    service = get_tts_service({"provider": "aliyun", "api_key": "k"})
    assert isinstance(service, AliyunTTS)
    assert service.is_available()


def test_factory_default_volcano():
    service = get_tts_service({"api_key": "k"})
    assert isinstance(service, VolcanoTTS)


def test_factory_unsupported():
    with pytest.raises(ValueError):
        get_tts_service({"provider": "unknown"})


def test_volcano_not_available_without_creds():
    assert not VolcanoTTS().is_available()
    assert not VolcanoTTS(api_key="k", secret_key="s", appid="").is_available()


def test_aliyun_not_available_without_key():
    assert not AliyunTTS().is_available()


async def test_volcano_synthesize_decodes_audio():
    tts_body = []
    service = VolcanoTTS(
        "ak", "sk", "app", transport=httpx.MockTransport(_volcano_ok_handler(tts_body))
    )
    audio = await service.synthesize("你好", "zh-CN", speed=1.1, volume=0.9, output_format="mp3")
    assert audio == b"part-1-part-2"
    assert tts_body[0]["audio"]["voice_type"] == "zh-CN"
    assert tts_body[0]["audio"]["speed_ratio"] == 1.1
    assert tts_body[0]["app"]["token"] == "test-token"


async def test_volcano_synthesize_refreshes_token_on_401():
    calls = {"tts": 0}
    token_payload = {
        "code": 3000,
        "message": "Success",
        "data": {"token": "test-token", "expire_time": 604800},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/token"):
            return httpx.Response(200, json=token_payload)
        calls["tts"] += 1
        if calls["tts"] == 1:
            return httpx.Response(401, json={})
        return httpx.Response(
            200,
            json={
                "code": 3000,
                "message": "Success",
                "data": [{"data": base64.b64encode(b"ok").decode(), "index": 0, "type": "binary"}],
            },
        )

    service = VolcanoTTS("ak", "sk", "app", transport=httpx.MockTransport(handler))
    audio = await service.synthesize("hi", "zh")
    assert audio == b"ok"


async def test_volcano_synthesize_raises_on_nonzero_code():
    token_payload = {
        "code": 3000,
        "message": "Success",
        "data": {"token": "t", "expire_time": 604800},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/token"):
            return httpx.Response(200, json=token_payload)
        return httpx.Response(200, json={"code": 40000, "message": "bad voice"})

    service = VolcanoTTS("ak", "sk", "app", transport=httpx.MockTransport(handler))
    with pytest.raises(RuntimeError):
        await service.synthesize("hi", "bad")


async def test_aliyun_synthesize_returns_audio():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, content=b"audio-mp3")

    service = AliyunTTS("ak", transport=httpx.MockTransport(handler))
    audio = await service.synthesize(
        "你好", "sambert-zhichu-v1", speed=0.8, volume=0.5, output_format="mp3"
    )
    assert audio == b"audio-mp3"
    assert captured["auth"] == "Bearer ak"
    assert captured["body"]["model"] == "sambert-zhichu-v1"
    assert captured["body"]["parameters"]["rate"] == 0.8
    assert captured["body"]["parameters"]["volume"] == 50
    assert captured["body"]["parameters"]["format"] == "mp3"
