from app.models.setting import Setting
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
    assert data["music_config"]["provider"] == "minimax"
    assert data["music_config"]["minimax"]["model"] == "music-3.0"
    assert data["music_config"]["minimax"]["source_format"] == "mp3"
    assert data["music_config"]["aliyun"]["model"] == "fun-music-v1"


async def test_save_settings(client):
    payload = SettingSchema(
        llm_config=LLMConfig(),
        tts_config=TTSConfig(),
        dify_config=DifyConfig(),
        general_config=GeneralConfig(),
    ).model_dump()
    payload["llm_config"]["api_key"] = "sk-test"
    payload["dify_config"]["script_app_key"] = "app-xxx"
    payload["music_config"]["minimax"]["api_key"] = "minimax-key"
    payload["music_config"]["minimax"]["source_format"] = "wav"
    payload["music_config"]["aliyun"]["api_key"] = "music-key"
    payload["music_config"]["aliyun"]["workspace_id"] = "workspace"
    resp = await client.post("/api/settings", json=payload)
    assert resp.status_code == 200
    assert resp.json()["llm_config"]["api_key"] == "sk-test"

    resp = await client.get("/api/settings")
    assert resp.json()["llm_config"]["api_key"] == "sk-test"
    assert resp.json()["dify_config"]["script_app_key"] == "app-xxx"
    assert resp.json()["music_config"]["minimax"]["api_key"] == "minimax-key"
    assert resp.json()["music_config"]["minimax"]["source_format"] == "wav"
    assert resp.json()["music_config"]["aliyun"]["api_key"] == "music-key"


async def test_get_settings_normalizes_legacy_flat_music_config(
    client, db_session
):
    async with db_session() as db:
        db.add(
            Setting(
                id=1,
                music_config={
                    "provider": "aliyun",
                    "api_key": "legacy-key",
                    "workspace_id": "legacy-workspace",
                    "base_url": "https://legacy.example/api/v1",
                    "model": "fun-music-v1",
                    "source_format": "wav",
                    "worker_concurrency": 2,
                },
            )
        )
        await db.commit()

    response = await client.get("/api/settings")
    assert response.status_code == 200
    music = response.json()["music_config"]
    assert music["provider"] == "minimax"
    assert music["aliyun"]["api_key"] == "legacy-key"
    assert music["aliyun"]["workspace_id"] == "legacy-workspace"
    assert music["aliyun"]["base_url"] == "https://legacy.example/api/v1"
    assert music["minimax"]["model"] == "music-3.0"
    assert music["minimax"]["base_url"] == "https://api.minimaxi.com/v1"
    assert music["worker_concurrency"] == 2


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
