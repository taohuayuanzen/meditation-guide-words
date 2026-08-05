async def _create_script(client):
    resp = await client.post("/api/scripts", json={"title": "脚本", "content": "正文"})
    assert resp.status_code == 201
    return resp.json()


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
