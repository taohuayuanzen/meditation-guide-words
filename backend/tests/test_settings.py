from app.schemas.setting import DifyConfig, GeneralConfig, LLMConfig, SettingSchema, TTSConfig


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
