from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models.music_task import MusicTask
from app.models.setting import Setting


async def _configure_music(db_session):
    async with db_session() as db:
        db.add(
            Setting(
                id=1,
                music_config={
                    "provider": "aliyun",
                    "output_format": "mp3",
                    "enable_aigc_watermark": False,
                    "worker_concurrency": 1,
                    "aliyun": {
                        "api_key": "music-secret-key",
                        "workspace_id": "workspace-1",
                        "base_url": "",
                        "model": "fun-music-v1",
                        "source_format": "wav",
                    },
                    "minimax": {
                        "api_key": "minimax-secret-key",
                        "base_url": "https://api.minimaxi.com/v1",
                        "model": "music-3.0",
                        "source_format": "mp3",
                    },
                },
            )
        )
        await db.commit()


def _payload(**overrides):
    payload = {
        "prompt": "后半段逐渐安静",
        "effective_prompt": "创作用于睡前冥想的纯音乐",
        "preset_params": {"scene": "sleep", "moods": ["calm"]},
        "target_duration_seconds": 600,
    }
    payload.update(overrides)
    return payload


async def test_create_list_and_detail_music_task(client, db_session):
    await _configure_music(db_session)
    response = await client.post(
        "/api/music-tasks",
        json={
            **_payload(),
            "model": "client-model",
            "source_format": "mp3",
            "is_instrumental": False,
            "enable_aigc_watermark": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["model"] == "fun-music-v1"
    assert data["provider"] == "aliyun"
    assert data["source_format"] == "wav"
    assert data["status"] == "pending"
    assert data["stage"] == "generating"
    assert data["output_format"] == "mp3"
    assert data["watermark_enabled"] is False
    assert data["is_ai_generated"] is True
    assert "remote_audio_url" not in data
    assert "music-secret-key" not in response.text

    task_id = data["id"]
    detail = await client.get(f"/api/music-tasks/{task_id}")
    assert detail.status_code == 200
    assert detail.json()["effective_prompt"] == "创作用于睡前冥想的纯音乐"
    listing = await client.get("/api/music-tasks")
    assert [item["id"] for item in listing.json()] == [task_id]


async def test_create_requires_music_config(client):
    response = await client.post("/api/music-tasks", json=_payload())
    assert response.status_code == 400
    assert "API Key" in response.json()["detail"]


async def test_prompt_and_duration_validation(client, db_session):
    await _configure_music(db_session)
    for duration in (59, 3601):
        response = await client.post(
            "/api/music-tasks", json=_payload(target_duration_seconds=duration)
        )
        assert response.status_code == 422
    empty_prompt_response = await client.post(
        "/api/music-tasks", json=_payload(effective_prompt="   ")
    )
    assert empty_prompt_response.status_code == 422
    assert (
        await client.post("/api/music-tasks", json=_payload(effective_prompt="x" * 2001))
    ).status_code == 422


async def test_task_response_never_exposes_signed_url(client, db_session):
    await _configure_music(db_session)
    async with db_session() as db:
        task = MusicTask(
            prompt="p",
            effective_prompt="effective",
            preset_params={},
            model="fun-music-v1",
            status="failed",
            stage="downloading",
            target_duration_seconds=600,
            output_format="mp3",
            is_ai_generated=True,
            watermark_enabled=False,
            request_id="request-1",
            remote_audio_url="https://oss.example/a.wav?signature=never-expose",
            remote_url_expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        task_id = task.id

    for path in ("/api/music-tasks", f"/api/music-tasks/{task_id}"):
        response = await client.get(path)
        assert "remote_audio_url" not in response.text
        assert "signature=never-expose" not in response.text
        assert "music-secret-key" not in response.text


async def test_retry_with_url_resets_only_download_stage(client, db_session):
    await _configure_music(db_session)
    async with db_session() as db:
        task = MusicTask(
            prompt="p",
            effective_prompt="effective",
            preset_params={},
            model="fun-music-v1",
            status="failed",
            stage="downloading",
            retry_count=1,
            download_retry_count=2,
            request_id="request-1",
            remote_audio_url="https://oss.example/a.wav?signature=secret",
            remote_url_expires_at=datetime.now(UTC) + timedelta(hours=1),
            target_duration_seconds=600,
            output_format="mp3",
            is_ai_generated=True,
            watermark_enabled=False,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        task_id = task.id

    response = await client.post(f"/api/music-tasks/{task_id}/retry")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["stage"] == "downloading"
    assert response.json()["download_retry_count"] == 0
    assert response.json()["retry_count"] == 1

    async with db_session() as db:
        task = (await db.execute(select(MusicTask).where(MusicTask.id == task_id))).scalar_one()
        assert "signature=secret" in task.remote_audio_url


async def test_retry_without_remote_result_starts_new_generation_cycle(client, db_session):
    await _configure_music(db_session)
    async with db_session() as db:
        task = MusicTask(
            prompt="p",
            effective_prompt="effective",
            preset_params={},
            model="fun-music-v1",
            status="failed",
            stage="generating",
            retry_count=1,
            target_duration_seconds=600,
            output_format="mp3",
            is_ai_generated=True,
            watermark_enabled=False,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        task_id = task.id

    response = await client.post(f"/api/music-tasks/{task_id}/retry")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["stage"] == "generating"
    assert response.json()["retry_count"] == 0


async def test_retry_rejects_expired_url(client, db_session):
    await _configure_music(db_session)
    async with db_session() as db:
        task = MusicTask(
            prompt="p",
            effective_prompt="effective",
            preset_params={},
            model="fun-music-v1",
            status="failed",
            stage="downloading",
            request_id="request-1",
            remote_audio_url="https://oss.example/expired.wav?signature=secret",
            remote_url_expires_at=datetime.now(UTC) - timedelta(seconds=1),
            target_duration_seconds=600,
            output_format="mp3",
            is_ai_generated=True,
            watermark_enabled=False,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        task_id = task.id

    response = await client.post(f"/api/music-tasks/{task_id}/retry")
    assert response.status_code == 409
    assert "新建任务" in response.json()["detail"]


async def test_minimax_task_snapshot_and_regeneration_requires_confirmation(
    client, db_session
):
    async with db_session() as db:
        db.add(
            Setting(
                id=1,
                music_config={
                    "provider": "minimax",
                    "minimax": {
                        "api_key": "minimax-secret",
                        "base_url": "https://api.minimaxi.com/v1",
                        "source_format": "wav",
                    },
                    "aliyun": {
                        "api_key": "aliyun-secret",
                        "workspace_id": "workspace",
                    },
                },
            )
        )
        await db.commit()

    created = await client.post("/api/music-tasks", json=_payload())
    assert created.status_code == 201
    data = created.json()
    assert data["provider"] == "minimax"
    assert data["model"] == "music-3.0"
    assert data["source_format"] == "wav"
    assert data["estimated_cost"] is None

    task_id = data["id"]
    async with db_session() as db:
        task = await db.get(MusicTask, task_id)
        task.status = "failed"
        task.error_code = "MUSIC_TIMEOUT"
        task.error_msg = "timeout"
        await db.commit()

    rejected = await client.post(
        f"/api/music-tasks/{task_id}/retry", json={"confirm_regenerate": False}
    )
    assert rejected.status_code == 409
    assert "confirm_regenerate=true" in rejected.json()["detail"]
    confirmed = await client.post(
        f"/api/music-tasks/{task_id}/retry", json={"confirm_regenerate": True}
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["stage"] == "generating"
