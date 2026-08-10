from app.schemas.setting import DifyConfig, GeneralConfig, LLMConfig, SettingSchema, TTSConfig


class FakeTTS:
    def __init__(self, error=None):
        self.error = error

    def is_available(self):
        return True

    async def synthesize(self, *args, **kwargs):
        if self.error:
            raise self.error
        return b"audio"


async def test_get_default_settings(client):
    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["llm_config"]["provider"] == "deepseek"
    assert data["dify_config"]["base_url"] == "http://localhost/v1"
    assert data["general_config"]["language"] == "zh"


async def test_save_settings(client):
    payload = SettingSchema(
        llm_config=LLMConfig(),
        tts_config=TTSConfig(),
        dify_config=DifyConfig(),
        general_config=GeneralConfig(),
    ).model_dump()
    payload["llm_config"]["api_key"] = "sk-test"
    payload["dify_config"]["script_app_key"] = "app-xxx"
    resp = await client.post("/api/settings", json=payload)
    assert resp.status_code == 200
    assert resp.json()["llm_config"]["api_key"] == "sk-test"

    resp = await client.get("/api/settings")
    assert resp.json()["llm_config"]["api_key"] == "sk-test"
    assert resp.json()["dify_config"]["script_app_key"] == "app-xxx"


async def test_test_llm_missing_key(client):
    resp = await client.post("/api/settings/test-llm", json={})
    assert resp.status_code == 400
    assert "未配置" in resp.json()["detail"]


async def test_test_tts_missing_key(client):
    resp = await client.post("/api/settings/test-tts", json={})
    assert resp.status_code == 400
    assert "未配置" in resp.json()["detail"]


async def test_test_tts_missing_voice_id(client):
    resp = await client.post("/api/settings/test-tts", json={"provider": "aliyun", "api_key": "k"})
    assert resp.status_code == 400
    assert "音色" in resp.json()["detail"]


async def test_test_tts_real_synthesis(client, monkeypatch):
    from app.routers import settings as settings_router

    monkeypatch.setattr(settings_router, "get_tts_service", lambda cfg: FakeTTS())
    payload = {
        "provider": "volcano",
        "api_key": "k",
        "secret_key": "s",
        "appid": "a",
        "voice_id": "v",
    }
    resp = await client.post("/api/settings/test-tts", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_test_tts_synthesis_failure(client, monkeypatch):
    from app.routers import settings as settings_router

    monkeypatch.setattr(
        settings_router, "get_tts_service", lambda cfg: FakeTTS(error=RuntimeError("boom"))
    )
    resp = await client.post(
        "/api/settings/test-tts",
        json={"provider": "aliyun", "api_key": "k", "voice_id": "v"},
    )
    assert resp.status_code == 502
    assert "boom" in resp.json()["detail"]
