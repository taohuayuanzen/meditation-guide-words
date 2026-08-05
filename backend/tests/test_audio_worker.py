from sqlalchemy import select

from app.models.audio_task import AudioTask
from app.models.script import Script
from app.models.setting import Setting
from app.services import audio_worker

_TTS_CONFIG = {
    "provider": "volcano",
    "api_key": "k",
    "secret_key": "s",
    "appid": "a",
    "voice_id": "v",
}


class FakeTTS:
    def __init__(self, audio=b"fake-audio", error=None):
        self.audio = audio
        self.error = error

    async def synthesize(self, *args, **kwargs):
        if self.error:
            raise self.error
        return self.audio


async def _create_script(db_session, content="正文"):
    async with db_session() as db:
        script = Script(title="脚本", content=content)
        db.add(script)
        await db.commit()
        await db.refresh(script)
        return script.id


async def _create_setting(db_session, tts_config, audio_dir):
    async with db_session() as db:
        setting = Setting(
            id=1,
            tts_config=tts_config,
            general_config={"audio_output_dir": audio_dir},
        )
        db.add(setting)
        await db.commit()


async def _create_task(db_session, script_id, tts_params=None):
    async with db_session() as db:
        task = AudioTask(
            script_id=script_id,
            voice_prompt="温柔女声",
            tts_params=tts_params,
            status="pending",
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task.id


async def _get_task(db_session, task_id):
    async with db_session() as db:
        result = await db.execute(select(AudioTask).where(AudioTask.id == task_id))
        return result.scalar_one()


async def test_process_task_success(db_session, tmp_path, monkeypatch):
    await _create_setting(db_session, _TTS_CONFIG, str(tmp_path))
    script_id = await _create_script(db_session)
    task_id = await _create_task(db_session, script_id, tts_params={"voice_id": "v2"})

    monkeypatch.setattr(audio_worker, "get_tts_service", lambda cfg: FakeTTS())
    await audio_worker.process_task(task_id, session_factory=db_session)

    task = await _get_task(db_session, task_id)
    assert task.status == "completed"
    assert task.file_path == str(tmp_path / f"{task_id}.mp3")
    assert task.retry_count == 0
    assert task.error_msg is None
    assert (tmp_path / f"{task_id}.mp3").read_bytes() == b"fake-audio"


async def test_process_task_retry_then_failed(db_session, tmp_path, monkeypatch):
    await _create_setting(db_session, _TTS_CONFIG, str(tmp_path))
    script_id = await _create_script(db_session)
    task_id = await _create_task(db_session, script_id)

    monkeypatch.setattr(
        audio_worker, "get_tts_service", lambda cfg: FakeTTS(error=RuntimeError("boom"))
    )
    await audio_worker.process_task(task_id, session_factory=db_session)

    task = await _get_task(db_session, task_id)
    assert task.status == "pending"
    assert task.retry_count == 1
    assert "boom" in task.error_msg

    await audio_worker.process_task(task_id, session_factory=db_session)
    task = await _get_task(db_session, task_id)
    assert task.status == "failed"
    assert task.retry_count == 1


async def test_process_task_text_too_long(db_session, tmp_path):
    tts_config = {"provider": "aliyun", "api_key": "k", "voice_id": "sambert-zhichu-v1"}
    await _create_setting(db_session, tts_config, str(tmp_path))
    script_id = await _create_script(db_session, content="长" * 5001)
    task_id = await _create_task(db_session, script_id)

    await audio_worker.process_task(task_id, session_factory=db_session)
    task = await _get_task(db_session, task_id)
    assert task.status == "pending"
    assert task.retry_count == 1
    assert "文本过长" in task.error_msg

    await audio_worker.process_task(task_id, session_factory=db_session)
    task = await _get_task(db_session, task_id)
    assert task.status == "failed"


async def test_process_task_missing_voice(db_session, tmp_path):
    tts_config = {"provider": "volcano", "api_key": "k", "secret_key": "s", "appid": "a"}
    await _create_setting(db_session, tts_config, str(tmp_path))
    script_id = await _create_script(db_session)
    task_id = await _create_task(db_session, script_id)

    await audio_worker.process_task(task_id, session_factory=db_session)
    task = await _get_task(db_session, task_id)
    assert task.status == "pending"
    assert "未配置音色" in task.error_msg


async def test_worker_loop_processes_pending(db_session, monkeypatch):
    script_id = await _create_script(db_session)
    task_id = await _create_task(db_session, script_id)

    called = []

    async def fake_process(task_id, *, session_factory):
        called.append(task_id)

    monkeypatch.setattr(audio_worker, "process_task", fake_process)
    await audio_worker.worker_loop(
        concurrency=1,
        session_factory=db_session,
        poll_interval=0.001,
        max_batches=1,
    )
    assert called == [task_id]
