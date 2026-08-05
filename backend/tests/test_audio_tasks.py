from sqlalchemy import select

from app.models.audio_task import AudioTask


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
        task = (
            await db.execute(select(AudioTask).where(AudioTask.id == task_id))
        ).scalar_one()
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
