import os

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.audio_task import AudioTask


@pytest.fixture
def artifact_dirs(tmp_path, monkeypatch):
    audio_dir = tmp_path / "audio"
    script_dir = tmp_path / "scripts"
    audio_dir.mkdir()
    script_dir.mkdir()
    monkeypatch.setattr(settings, "audio_output_dir", str(audio_dir))
    return str(audio_dir), str(script_dir)


async def _create_script(client, title="测试引导词", content="请闭上眼睛..."):
    resp = await client.post("/api/scripts", json={"title": title, "content": content})
    assert resp.status_code == 201
    return resp.json()


async def _create_audio_task(client, script_id, audio_dir, filename="1.mp3"):
    resp = await client.post(
        "/api/audio-tasks",
        json={"script_id": script_id, "voice_prompt": "温柔女声"},
    )
    assert resp.status_code == 201
    task_id = resp.json()["id"]
    file_path = os.path.join(audio_dir, filename)
    with open(file_path, "wb") as f:
        f.write(b"fake audio")
    return task_id, file_path


async def test_create_script_writes_markdown(client, artifact_dirs):
    _, script_dir = artifact_dirs
    data = await _create_script(client, title="我的引导词", content="正文内容")
    expected_path = os.path.join(script_dir, f"我的引导词_{data['id']}.md")
    assert os.path.exists(expected_path)
    with open(expected_path, encoding="utf-8") as f:
        content = f.read()
    assert "# 我的引导词" in content
    assert "正文内容" in content


async def test_list_artifacts(client, artifact_dirs, db_session):
    audio_dir, script_dir = artifact_dirs

    script = await _create_script(client, title="引导词 A", content="内容 A")
    task_id, file_path = await _create_audio_task(client, script["id"], audio_dir)

    async with db_session() as db:
        task = (await db.execute(select(AudioTask).where(AudioTask.id == task_id))).scalar_one()
        task.status = "completed"
        task.file_path = file_path
        await db.commit()

    resp = await client.get("/api/artifacts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    items = body["items"]
    assert len(items) == 2

    audio_items = [i for i in items if i["type"] == "audio"]
    script_items = [i for i in items if i["type"] == "script"]
    assert len(audio_items) == 1
    assert len(script_items) == 1
    assert audio_items[0]["task_id"] == task_id
    assert script_items[0]["script_id"] == script["id"]


async def test_list_artifacts_filter_by_type(client, artifact_dirs, db_session):
    audio_dir, _ = artifact_dirs
    script = await _create_script(client)
    task_id, file_path = await _create_audio_task(client, script["id"], audio_dir)

    async with db_session() as db:
        task = (await db.execute(select(AudioTask).where(AudioTask.id == task_id))).scalar_one()
        task.status = "completed"
        task.file_path = file_path
        await db.commit()

    resp = await client.get("/api/artifacts?type=audio")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert all(i["type"] == "audio" for i in resp.json()["items"])


async def test_list_artifacts_paginates_by_created_time(client, artifact_dirs):
    _, script_dir = artifact_dirs
    scripts = []
    for index in range(21):
        scripts.append(await _create_script(client, title=f"引导词 {index}", content="内容"))

    resp = await client.get("/api/artifacts?type=script&page=1&page_size=20")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 21
    assert len(body["items"]) == 20
    assert body["items"][0]["script_id"] == scripts[-1]["id"]
    assert body["items"][-1]["script_id"] == scripts[1]["id"]

    resp = await client.get("/api/artifacts?type=script&page=2&page_size=20")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["script_id"] == scripts[0]["id"]

    orphan_path = os.path.join(script_dir, "孤立文件.md")
    with open(orphan_path, "w", encoding="utf-8") as f:
        f.write("内容")
    resp = await client.get("/api/artifacts?type=script&page=1&page_size=20")
    assert resp.status_code == 200
    assert resp.json()["items"][0]["name"] == "孤立文件.md"


async def test_download_script(client):
    script = await _create_script(client, title="可下载引导词", content="下载内容")
    resp = await client.get(f"/api/artifacts/script_{script['id']}/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/markdown; charset=utf-8"
    assert "# 可下载引导词" in resp.text
    assert "下载内容" in resp.text


async def test_rename_script(client, artifact_dirs):
    _, script_dir = artifact_dirs
    script = await _create_script(client, title="旧标题", content="内容")
    old_path = os.path.join(script_dir, f"旧标题_{script['id']}.md")
    assert os.path.exists(old_path)

    resp = await client.post(
        f"/api/artifacts/script_{script['id']}/rename",
        json={"new_name": "新标题"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == f"新标题_{script['id']}.md"

    new_path = os.path.join(script_dir, f"新标题_{script['id']}.md")
    assert os.path.exists(new_path)
    assert not os.path.exists(old_path)

    resp = await client.get(f"/api/scripts/{script['id']}")
    assert resp.json()["title"] == "新标题"


async def test_rename_audio(client, artifact_dirs, db_session):
    audio_dir, _ = artifact_dirs
    script = await _create_script(client)
    task_id, file_path = await _create_audio_task(client, script["id"], audio_dir, "old.mp3")

    async with db_session() as db:
        task = (await db.execute(select(AudioTask).where(AudioTask.id == task_id))).scalar_one()
        task.status = "completed"
        task.file_path = file_path
        await db.commit()

    resp = await client.post(
        f"/api/artifacts/audio_{task_id}/rename",
        json={"new_name": "睡前冥想"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "睡前冥想.mp3"

    new_path = os.path.join(audio_dir, "睡前冥想.mp3")
    assert os.path.exists(new_path)
    assert not os.path.exists(file_path)

    async with db_session() as db:
        task = (await db.execute(select(AudioTask).where(AudioTask.id == task_id))).scalar_one()
        assert task.file_path == new_path


async def test_rename_conflict(client, artifact_dirs, db_session):
    audio_dir, _ = artifact_dirs
    script = await _create_script(client)
    task1_id, file1_path = await _create_audio_task(client, script["id"], audio_dir, "a.mp3")
    task2_id, file2_path = await _create_audio_task(client, script["id"], audio_dir, "b.mp3")

    async with db_session() as db:
        for task_id, file_path in ((task1_id, file1_path), (task2_id, file2_path)):
            task = (await db.execute(select(AudioTask).where(AudioTask.id == task_id))).scalar_one()
            task.status = "completed"
            task.file_path = file_path
            await db.commit()

    resp = await client.post(
        f"/api/artifacts/audio_{task1_id}/rename",
        json={"new_name": "b"},
    )
    assert resp.status_code == 409


async def test_delete_script(client, artifact_dirs):
    _, script_dir = artifact_dirs
    script = await _create_script(client, title="待删除", content="内容")
    file_path = os.path.join(script_dir, f"待删除_{script['id']}.md")
    assert os.path.exists(file_path)

    resp = await client.delete(f"/api/artifacts/script_{script['id']}")
    assert resp.status_code == 204

    assert not os.path.exists(file_path)
    resp = await client.get(f"/api/scripts/{script['id']}")
    assert resp.status_code == 404


async def test_delete_audio(client, artifact_dirs, db_session):
    audio_dir, _ = artifact_dirs
    script = await _create_script(client)
    task_id, file_path = await _create_audio_task(client, script["id"], audio_dir)

    async with db_session() as db:
        task = (await db.execute(select(AudioTask).where(AudioTask.id == task_id))).scalar_one()
        task.status = "completed"
        task.file_path = file_path
        await db.commit()

    resp = await client.delete(f"/api/artifacts/audio_{task_id}")
    assert resp.status_code == 204

    assert not os.path.exists(file_path)
    resp = await client.get(f"/api/audio-tasks/{task_id}")
    assert resp.status_code == 404
