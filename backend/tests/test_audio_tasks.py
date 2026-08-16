from sqlalchemy import select

from app.models.audio_task import AudioTask
from app.models.script import Script
from app.models.setting import Setting
from app.schemas.audio_render_plan import AudioRenderPlan
from app.services.audio_renderer import canonical_digest
from app.services.render_plan_service import build_preview_digest, build_tts_snapshot


async def _create_script(client):
    resp = await client.post("/api/scripts", json={"title": "脚本", "content": "正文"})
    assert resp.status_code == 201
    return resp.json()


async def test_create_task_with_tts_params(client):
    script = await _create_script(client)
    resp = await client.post(
        "/api/audio-tasks",
        json={
            "script_id": script["id"],
            "voice_prompt": "温柔女声",
            "tts_params": {"voice_id": "v", "speed": 0.8, "volume": 1.0},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["retry_count"] == 0
    assert data["tts_params"] == {"voice_id": "v", "speed": 0.8, "volume": 1.0}


async def test_retry_resets_retry_count_and_file(client, db_session):
    script = await _create_script(client)
    resp = await client.post(
        "/api/audio-tasks",
        json={"script_id": script["id"], "voice_prompt": "a"},
    )
    task_id = resp.json()["id"]

    async with db_session() as db:
        task = (await db.execute(select(AudioTask).where(AudioTask.id == task_id))).scalar_one()
        task.status = "failed"
        task.retry_count = 2
        task.error_msg = "boom"
        task.file_path = "/tmp/old.mp3"
        task.completed_at = None
        await db.commit()

    resp = await client.post(f"/api/audio-tasks/{task_id}/retry")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["retry_count"] == 0
    assert data["file_path"] is None
    assert data["error_msg"] is None


async def test_create_task(client):
    script = await _create_script(client)
    resp = await client.post(
        "/api/audio-tasks",
        json={"script_id": script["id"], "voice_prompt": "温柔女声"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["script_id"] == script["id"]


async def test_list_tasks(client):
    script = await _create_script(client)
    await client.post("/api/audio-tasks", json={"script_id": script["id"], "voice_prompt": "a"})
    resp = await client.get("/api/audio-tasks")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_get_task_404(client):
    resp = await client.get("/api/audio-tasks/999")
    assert resp.status_code == 404


async def test_download_not_ready(client):
    script = await _create_script(client)
    resp = await client.post(
        "/api/audio-tasks",
        json={"script_id": script["id"], "voice_prompt": "a"},
    )
    task_id = resp.json()["id"]
    resp = await client.get(f"/api/audio-tasks/{task_id}/download")
    assert resp.status_code == 404


async def test_retry_task(client):
    script = await _create_script(client)
    resp = await client.post(
        "/api/audio-tasks",
        json={"script_id": script["id"], "voice_prompt": "a"},
    )
    task_id = resp.json()["id"]

    resp = await client.post(f"/api/audio-tasks/{task_id}/retry")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


async def test_audio_capabilities(client):
    response = await client.get("/api/audio-tasks/capabilities")
    assert response.status_code == 200
    assert response.json() == {
        "ffmpeg_available": True,
        "ffprobe_available": True,
        "audio_rendering_available": True,
    }


async def test_structured_task_uses_server_preview_digest_and_safe_snapshot(client, db_session):
    script_response = await client.post(
        "/api/scripts",
        json={
            "title": "结构化脚本",
            "script_plan": {
                "version": 1,
                "target_duration_seconds": 60,
                "blocks": [{"text": "感受呼吸。", "pause_after": {"kind": "short"}}],
            },
        },
    )
    script_data = script_response.json()
    block = script_data["script_plan"]["blocks"][0]
    tts_config = {
        "provider": "aliyun",
        "api_key": "secret-api-key",
        "secret_key": "secret",
        "model": "qwen-audio-3.0-tts-plus",
        "voice_id": "longanlingxin",
        "base_url": "https://dashscope.aliyuncs.com/api/v1?token=secret",
    }
    async with db_session() as db:
        db.add(Setting(id=1, tts_config=tts_config))
        await db.commit()
        script = await db.get(Script, script_data["id"])
        plan = AudioRenderPlan.model_validate(
            {
                "version": 1,
                "pause_profile_id": "standard_v1",
                "voice": {
                    "voice_id": "longanlingxin",
                    "rate": 0.9,
                    "volume": 1,
                    "pitch": 1,
                    "instruction": "温柔平静",
                },
                "segments": [
                    {
                        "id": block["id"],
                        "text": block["text"],
                        "pause_after_ms": 700,
                        "pause_kind": "short",
                        "pause_strategy": "natural",
                    }
                ],
            }
        )
        plan_data = plan.model_dump(mode="json")
        plan_digest = canonical_digest(plan_data)
        snapshot = build_tts_snapshot(tts_config, plan)
        preview_digest = build_preview_digest(script, plan_digest, tts_config, snapshot)

    response = await client.post(
        "/api/audio-tasks",
        json={
            "script_id": script_data["id"],
            "voice_prompt": "温柔平静",
            "render_plan": plan_data,
            "render_plan_digest": plan_digest,
            "preview_digest": preview_digest,
        },
    )
    assert response.status_code == 201, response.text
    task_id = response.json()["id"]
    async with db_session() as db:
        task = await db.get(AudioTask, task_id)
        serialized = str(task.tts_snapshot).lower()
        assert "secret-api-key" not in serialized
        assert "authorization" not in serialized
        assert "?token=" not in serialized


async def test_structured_task_rejects_preview_after_tts_config_change(client, db_session):
    # Reuse the end-to-end creation test's protocol with an intentionally stale digest.
    script_response = await client.post(
        "/api/scripts",
        json={
            "title": "冲突脚本",
            "script_plan": {
                "version": 1,
                "target_duration_seconds": 60,
                "blocks": [{"text": "呼吸。", "pause_after": {"kind": "short"}}],
            },
        },
    )
    script_data = script_response.json()
    block = script_data["script_plan"]["blocks"][0]
    plan_data = {
        "version": 1,
        "pause_profile_id": "standard_v1",
        "voice": {
            "voice_id": "longanlingxin",
            "rate": 0.9,
            "volume": 1,
            "pitch": 1,
            "instruction": "温柔平静",
        },
        "segments": [
            {
                "id": block["id"],
                "text": block["text"],
                "pause_after_ms": 700,
                "pause_kind": "short",
                "pause_strategy": "natural",
            }
        ],
    }
    async with db_session() as db:
        db.add(
            Setting(
                id=1,
                tts_config={
                    "provider": "aliyun",
                    "api_key": "k",
                    "model": "qwen-audio-3.0-tts-plus",
                    "voice_id": "longanlingxin",
                },
            )
        )
        await db.commit()
    response = await client.post(
        "/api/audio-tasks",
        json={
            "script_id": script_data["id"],
            "voice_prompt": "温柔平静",
            "render_plan": plan_data,
            "render_plan_digest": canonical_digest(plan_data),
            "preview_digest": "sha256:stale",
        },
    )
    assert response.status_code == 409
    assert "预览已过期" in response.json()["detail"]


async def test_delete_task_cleans_final_work_and_part_files(client, db_session, tmp_path):
    script = await _create_script(client)
    response = await client.post(
        "/api/audio-tasks", json={"script_id": script["id"], "voice_prompt": "温柔"}
    )
    task_id = response.json()["id"]
    async with db_session() as db:
        db.add(Setting(id=1, general_config={"audio_output_dir": str(tmp_path)}))
        await db.commit()
    work = tmp_path / "work" / str(task_id)
    work.mkdir(parents=True)
    final = tmp_path / f"{task_id}.mp3"
    part = tmp_path / f"{task_id}.mp3.part"
    final.write_bytes(b"audio")
    part.write_bytes(b"partial")
    (work / "speech_000.wav").write_bytes(b"segment")
    response = await client.delete(f"/api/audio-tasks/{task_id}")
    assert response.status_code == 204
    assert not final.exists()
    assert not part.exists()
    assert not work.exists()
