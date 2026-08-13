from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select

from app.models.music_task import MusicTask
from app.models.setting import Setting
from app.services.music_aliyun import MusicGenerationResult, MusicServiceError
from app.services.music_postprocessor import AudioInfo
from app.services.music_worker import process_task


async def _create_setting(db_session):
    async with db_session() as db:
        db.add(
            Setting(
                id=1,
                music_config={
                    "api_key": "key",
                    "workspace_id": "workspace",
                    "model": "fun-music-v1",
                },
            )
        )
        await db.commit()


async def _create_task(db_session, **overrides):
    values = {
        "prompt": "prompt",
        "effective_prompt": "effective prompt",
        "preset_params": {},
        "model": "fun-music-v1",
        "status": "pending",
        "stage": "generating",
        "target_duration_seconds": 600,
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


async def _get_task(db_session, task_id):
    async with db_session() as db:
        result = await db.execute(select(MusicTask).where(MusicTask.id == task_id))
        return result.scalar_one()


def _result():
    return MusicGenerationResult(
        request_id="request-1",
        audio_id="audio-1",
        audio_url="https://oss.example/audio.wav?signature=secret",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        channels=2,
        sample_rate=48000,
        duration_seconds=200,
    )


def _fake_postprocess(source_path, final_path, target_duration_seconds):
    final_path.write_bytes(b"mp3-bytes")
    return (
        AudioInfo(duration_seconds=198.4, sample_rate=48000, channels=2),
        AudioInfo(
            duration_seconds=float(target_duration_seconds),
            sample_rate=48000,
            channels=2,
        ),
    )


async def test_generation_result_is_persisted_before_download_retry(db_session, tmp_path):
    await _create_setting(db_session)
    task_id = await _create_task(db_session)
    calls = 0

    async def fake_generate(config, prompt):
        nonlocal calls
        calls += 1
        return _result()

    transport = httpx.MockTransport(
        lambda request: httpx.Response(503, text="temporary failure")
    )
    await process_task(
        task_id,
        session_factory=db_session,
        source_dir=tmp_path,
        final_dir=tmp_path,
        generate=fake_generate,
        postprocess=_fake_postprocess,
        download_transport=transport,
    )
    task = await _get_task(db_session, task_id)
    assert calls == 1
    assert task.request_id == "request-1"
    assert task.remote_audio_url.startswith("https://oss.example/")
    assert task.source_duration_seconds == 200
    assert task.estimated_cost == 0.4
    assert task.status == "pending"
    assert task.stage == "downloading"
    assert task.download_retry_count == 1

    async def must_not_generate(config, prompt):
        raise AssertionError("model must not be called after URL persistence")

    await process_task(
        task_id,
        session_factory=db_session,
        source_dir=tmp_path,
        final_dir=tmp_path,
        generate=must_not_generate,
        postprocess=_fake_postprocess,
        download_transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"wav-bytes")
        ),
    )
    task = await _get_task(db_session, task_id)
    assert task.status == "completed"
    assert task.stage == "processing"
    assert task.source_duration_seconds == 198
    assert (tmp_path / f"{task_id}.wav").read_bytes() == b"wav-bytes"


async def test_model_call_retries_only_once(db_session, tmp_path):
    await _create_setting(db_session)
    task_id = await _create_task(db_session)
    calls = 0

    async def fail(config, prompt):
        nonlocal calls
        calls += 1
        raise MusicServiceError("MUSIC_TIMEOUT", "timeout", retryable=True)

    await process_task(
        task_id,
        session_factory=db_session,
        source_dir=tmp_path,
        final_dir=tmp_path,
        generate=fail,
    )
    task = await _get_task(db_session, task_id)
    assert task.status == "pending"
    assert task.retry_count == 1

    await process_task(
        task_id,
        session_factory=db_session,
        source_dir=tmp_path,
        final_dir=tmp_path,
        generate=fail,
    )
    task = await _get_task(db_session, task_id)
    assert calls == 2
    assert task.status == "failed"
    assert task.retry_count == 1


async def test_download_reuses_url_and_has_two_extra_retries(db_session, tmp_path):
    task_id = await _create_task(
        db_session,
        remote_audio_url="https://oss.example/audio.wav?signature=secret",
        request_id="request-1",
        remote_url_expires_at=datetime.now(UTC) + timedelta(hours=1),
        stage="downloading",
    )
    download_calls = 0

    def fail_download(request):
        nonlocal download_calls
        download_calls += 1
        return httpx.Response(500)

    async def must_not_generate(config, prompt):
        raise AssertionError("existing URL must be reused")

    transport = httpx.MockTransport(fail_download)
    for _ in range(3):
        await process_task(
            task_id,
            session_factory=db_session,
            source_dir=tmp_path,
            final_dir=tmp_path,
            generate=must_not_generate,
            download_transport=transport,
        )
    task = await _get_task(db_session, task_id)
    assert download_calls == 3
    assert task.download_retry_count == 2
    assert task.status == "failed"
    assert not (tmp_path / f"{task_id}.wav").exists()
    assert not (tmp_path / f"{task_id}.wav.part").exists()


async def test_existing_wav_recovers_directly_to_source_ready(db_session, tmp_path):
    task_id = await _create_task(db_session, status="failed")
    (tmp_path / f"{task_id}.wav").write_bytes(b"existing-wav")

    async def must_not_generate(config, prompt):
        raise AssertionError("existing WAV must win")

    await process_task(
        task_id,
        session_factory=db_session,
        source_dir=tmp_path,
        final_dir=tmp_path,
        generate=must_not_generate,
        postprocess=_fake_postprocess,
    )
    task = await _get_task(db_session, task_id)
    assert task.status == "completed"
    assert task.stage == "processing"


async def test_expired_url_fails_without_regeneration(db_session, tmp_path):
    task_id = await _create_task(
        db_session,
        remote_audio_url="https://oss.example/expired.wav?secret=yes",
        request_id="request-1",
        remote_url_expires_at=datetime.now(UTC) - timedelta(seconds=1),
        stage="downloading",
    )

    async def must_not_generate(config, prompt):
        raise AssertionError("expired URL must not trigger regeneration")

    await process_task(
        task_id,
        session_factory=db_session,
        source_dir=tmp_path,
        final_dir=tmp_path,
        generate=must_not_generate,
    )
    task = await _get_task(db_session, task_id)
    assert task.status == "failed"
    assert task.error_code == "MUSIC_URL_EXPIRED"


async def test_part_file_is_not_treated_as_complete(db_session, tmp_path):
    task_id = await _create_task(db_session)
    (tmp_path / f"{task_id}.wav.part").write_bytes(b"partial")

    async def fail(config, prompt):
        raise MusicServiceError("MUSIC_AUTH_FAILED", "bad key")

    await process_task(
        task_id,
        session_factory=db_session,
        source_dir=tmp_path,
        final_dir=tmp_path,
        generate=fail,
    )
    task = await _get_task(db_session, task_id)
    assert task.status == "failed"
    assert task.stage == "generating"


async def test_minimax_generation_failure_is_never_automatically_retried(
    db_session, tmp_path
):
    async with db_session() as db:
        db.add(
            Setting(
                id=1,
                music_config={
                    "provider": "minimax",
                    "minimax": {"api_key": "key", "source_format": "mp3"},
                    "aliyun": {},
                },
            )
        )
        await db.commit()
    task_id = await _create_task(
        db_session,
        provider="minimax",
        model="music-3.0",
        source_format="wav",
    )
    calls = 0

    async def fail(config, prompt):
        nonlocal calls
        calls += 1
        assert config["source_format"] == "wav"
        raise MusicServiceError("MUSIC_TIMEOUT", "timeout", retryable=True)

    await process_task(
        task_id,
        session_factory=db_session,
        source_dir=tmp_path,
        final_dir=tmp_path,
        generate=fail,
    )
    task = await _get_task(db_session, task_id)
    assert calls == 1
    assert task.status == "failed"
    assert task.retry_count == 0
    assert "未自动重试" in task.error_msg
