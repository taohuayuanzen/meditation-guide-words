import httpx
from fastapi import Request

from app.routers import dify_proxy


def _receive_body(body: bytes):
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


def _make_request(body: bytes) -> Request:
    return Request(
        scope={
            "type": "http",
            "method": "POST",
            "headers": [[b"content-type", b"application/json"]],
        },
        receive=_receive_body(body),
    )


async def test_chat_script_fails_without_config(client, monkeypatch):
    monkeypatch.setattr(dify_proxy.settings, "dify_script_app_key", "")
    monkeypatch.setattr(dify_proxy.settings, "dify_audio_app_key", "")
    monkeypatch.setattr(dify_proxy.settings, "dify_base_url", "http://localhost/v1")
    resp = await client.post(
        "/api/dify/script/chat",
        json={"inputs": {}, "query": "hi", "response_mode": "streaming", "user": "u"},
    )
    assert resp.status_code == 400
    assert "Dify 配置未完成" in resp.json()["detail"]


async def test_chat_script_uses_env_config_when_db_empty(client, monkeypatch):
    monkeypatch.setattr(dify_proxy.settings, "dify_script_app_key", "env-script-key")
    monkeypatch.setattr(dify_proxy.settings, "dify_base_url", "http://dify.env/v1")

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, content=b"data: ok\n\n")

    request = _make_request(b'{"inputs":{},"query":"hi","response_mode":"streaming","user":"u"}')
    response = await dify_proxy.stream_dify(
        request, "env-script-key", "http://dify.env/v1", transport=httpx.MockTransport(handler)
    )
    body = b"".join([chunk async for chunk in response.body_iterator])
    assert captured["url"] == "http://dify.env/v1/chat-messages"
    assert captured["auth"] == "Bearer env-script-key"
    assert b"data: ok" in body


async def test_chat_script_prefers_db_config_over_env(client, monkeypatch):
    from app.schemas.setting import DifyConfig, GeneralConfig, LLMConfig, SettingSchema, TTSConfig

    payload = SettingSchema(
        llm_config=LLMConfig(),
        tts_config=TTSConfig(),
        dify_config=DifyConfig(script_app_key="db-script-key", base_url="http://dify.db/v1"),
        general_config=GeneralConfig(),
    ).model_dump()
    resp = await client.post("/api/settings", json=payload)
    assert resp.status_code == 200

    monkeypatch.setattr(dify_proxy.settings, "dify_script_app_key", "env-script-key")
    monkeypatch.setattr(dify_proxy.settings, "dify_base_url", "http://dify.env/v1")

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, content=b"data: ok\n\n")

    request = _make_request(b'{"inputs":{},"query":"hi","response_mode":"streaming","user":"u"}')
    response = await dify_proxy.stream_dify(
        request, "db-script-key", "http://dify.db/v1", transport=httpx.MockTransport(handler)
    )
    body = b"".join([chunk async for chunk in response.body_iterator])
    assert captured["url"] == "http://dify.db/v1/chat-messages"
    assert captured["auth"] == "Bearer db-script-key"
    assert b"data: ok" in body


async def test_stream_dify_returns_error_event_on_dify_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="Unauthorized")

    request = _make_request(b'{"inputs":{},"query":"hi","response_mode":"streaming","user":"u"}')
    response = await dify_proxy.stream_dify(
        request, "bad-key", "http://dify.test/v1", transport=httpx.MockTransport(handler)
    )
    body = b"".join([chunk async for chunk in response.body_iterator])
    assert b'"event": "error"' in body
    assert b"401" in body


async def test_stream_dify_returns_error_event_on_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    request = _make_request(b'{"inputs":{},"query":"hi","response_mode":"streaming","user":"u"}')
    response = await dify_proxy.stream_dify(
        request, "key", "http://dify.test/v1", transport=httpx.MockTransport(handler)
    )
    body = b"".join([chunk async for chunk in response.body_iterator])
    assert b'"event": "error"' in body
    assert "Dify 连接失败".encode() in body
