from app.schemas.audio_render_plan import RenderPlanPreviewResponse


async def test_pause_profiles_api(client):
    response = await client.get("/api/audio-render-plans/pause-profiles")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [
        "gentle_v1",
        "standard_v1",
        "deep_v1",
    ]


async def test_old_script_cannot_preview(client):
    script = await client.post("/api/scripts", json={"title": "旧脚本", "content": "正文"})
    response = await client.post(
        "/api/audio-render-plans/preview",
        json={
            "script_id": script.json()["id"],
            "pause_profile_id": "standard_v1",
            "voice_prompt": "温柔平静",
        },
    )
    assert response.status_code == 422
    assert "旧格式脚本" in response.json()["detail"]


async def test_preview_api_does_not_create_audio_task(client, monkeypatch):
    script = await client.post(
        "/api/scripts",
        json={
            "title": "新脚本",
            "script_plan": {
                "version": 1,
                "target_duration_seconds": 60,
                "blocks": [{"text": "感受呼吸。", "pause_after": {"kind": "short"}}],
            },
        },
    )

    async def fake_preview(db, stored_script, profile_id, voice_prompt):
        assert stored_script.id == script.json()["id"]
        return RenderPlanPreviewResponse.model_validate(
            {
                "render_plan": {
                    "version": 1,
                    "pause_profile_id": profile_id,
                    "voice": {
                        "voice_id": "longanlingxin",
                        "rate": 0.9,
                        "volume": 1,
                        "pitch": 1,
                        "instruction": voice_prompt,
                    },
                    "segments": [
                        {
                            "id": "b1",
                            "text": "感受呼吸。",
                            "pause_after_ms": 700,
                            "pause_kind": "short",
                            "pause_strategy": "natural",
                        }
                    ],
                },
                "render_plan_digest": "sha256:plan",
                "preview_digest": "sha256:preview",
                "estimate": {
                    "estimated_speech_seconds": 2,
                    "estimated_natural_pause_seconds": 1,
                    "deterministic_pause_seconds": 0,
                    "estimated_total_seconds": 3,
                    "target_duration_seconds": 60,
                    "duration_delta_seconds": -57,
                    "estimation_version": "zh_v1",
                },
            }
        )

    monkeypatch.setattr("app.routers.audio_render_plans.preview_render_plan", fake_preview)
    before = (await client.get("/api/audio-tasks")).json()
    response = await client.post(
        "/api/audio-render-plans/preview",
        json={
            "script_id": script.json()["id"],
            "pause_profile_id": "standard_v1",
            "voice_prompt": "温柔平静",
        },
    )
    after = (await client.get("/api/audio-tasks")).json()
    assert response.status_code == 200
    assert before == after == []
