from app.config import settings
from app.models.music_task import MusicTask


async def _task(db_session, **overrides):
    values = {
        "prompt": "p",
        "effective_prompt": "effective",
        "preset_params": {"moods": ["calm"]},
        "model": "fun-music-v1",
        "status": "completed",
        "stage": "processing",
        "target_duration_seconds": 300,
        "source_duration_seconds": 198,
        "final_duration_seconds": 300,
        "output_format": "mp3",
        "is_ai_generated": True,
        "watermark_enabled": False,
    }
    values.update(overrides)
    async with db_session() as db:
        task = MusicTask(**values)
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task.id


async def test_downloads_only_list_existing_files(client, db_session, tmp_path, monkeypatch):
    source_dir = tmp_path / "source"
    final_dir = tmp_path / "final"
    source_dir.mkdir()
    final_dir.mkdir()
    monkeypatch.setattr(settings, "music_source_dir", str(source_dir))
    monkeypatch.setattr(settings, "music_final_dir", str(final_dir))
    task_id = await _task(db_session)
    (source_dir / f"{task_id}.wav").write_bytes(b"wav")

    response = await client.get(f"/api/music-tasks/{task_id}/downloads")
    assert response.status_code == 200
    assert [item["kind"] for item in response.json()["items"]] == ["source"]
    download = await client.get(f"/api/music-tasks/{task_id}/download/source")
    assert download.status_code == 200
    assert download.content == b"wav"
    assert (await client.get(f"/api/music-tasks/{task_id}/download/final")).status_code == 404


async def test_delete_completed_removes_all_files_and_record(
    client, db_session, tmp_path, monkeypatch
):
    source_dir = tmp_path / "source"
    final_dir = tmp_path / "final"
    source_dir.mkdir()
    final_dir.mkdir()
    monkeypatch.setattr(settings, "music_source_dir", str(source_dir))
    monkeypatch.setattr(settings, "music_final_dir", str(final_dir))
    task_id = await _task(db_session)
    paths = [
        source_dir / f"{task_id}.wav",
        source_dir / f"{task_id}.wav.part",
        final_dir / f"{task_id}_5min.mp3",
        final_dir / f"{task_id}_5min.mp3.part",
        final_dir / f"{task_id}_5min.loop.part.wav",
    ]
    for path in paths:
        path.write_bytes(b"data")
    response = await client.delete(f"/api/music-tasks/{task_id}")
    assert response.status_code == 204
    assert all(not path.exists() for path in paths)
    assert (await client.get(f"/api/music-tasks/{task_id}")).status_code == 404


async def test_processing_task_cannot_be_deleted(client, db_session):
    task_id = await _task(db_session, status="processing")
    response = await client.delete(f"/api/music-tasks/{task_id}")
    assert response.status_code == 409
    assert "不支持取消" in response.json()["detail"]


async def test_minimax_source_mp3_has_correct_label_mime_and_cleanup(
    client, db_session, tmp_path, monkeypatch
):
    source_dir = tmp_path / "source"
    final_dir = tmp_path / "final"
    source_dir.mkdir()
    final_dir.mkdir()
    monkeypatch.setattr(settings, "music_source_dir", str(source_dir))
    monkeypatch.setattr(settings, "music_final_dir", str(final_dir))
    task_id = await _task(
        db_session, provider="minimax", model="music-3.0", source_format="mp3"
    )
    source = source_dir / f"{task_id}.mp3"
    part = source_dir / f"{task_id}.mp3.part"
    source.write_bytes(b"mp3")
    part.write_bytes(b"partial")

    listing = await client.get(f"/api/music-tasks/{task_id}/downloads")
    assert listing.json()["items"][0]["label"] == "原始 MP3"
    download = await client.get(f"/api/music-tasks/{task_id}/download/source")
    assert download.headers["content-type"].startswith("audio/mpeg")

    assert (await client.delete(f"/api/music-tasks/{task_id}")).status_code == 204
    assert not source.exists()
    assert not part.exists()
