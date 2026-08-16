import pytest

from app.models.audio_task import AudioTask
from app.services import audio_renderer
from app.services.audio_renderer import (
    MAX_TTS_REQUESTS,
    AudioRenderer,
    build_speech_segments,
    canonical_digest,
)
from app.services.music_postprocessor import AudioInfo
from app.services.tts_capabilities import get_tts_capabilities


def test_natural_pauses_are_merged_and_silence_splits_requests():
    plan = {
        "segments": [
            {"text": "一", "pause_strategy": "natural", "pause_after_ms": 300},
            {"text": "二", "pause_strategy": "silence", "pause_after_ms": 5000},
            {"text": "三", "pause_strategy": "natural", "pause_after_ms": 200},
        ]
    }
    segments = build_speech_segments(plan)
    assert [(item.text, item.pause_after_ms) for item in segments] == [
        ("一\n二", 5000),
        ("三", 0),
    ]


def test_request_limit_is_enforced():
    plan = {
        "segments": [
            {"text": str(index), "pause_strategy": "silence", "pause_after_ms": 1000}
            for index in range(MAX_TTS_REQUESTS + 1)
        ]
    }
    try:
        build_speech_segments(plan)
    except ValueError as exc:
        assert "上限" in str(exc)
    else:
        raise AssertionError("request limit was not enforced")


def test_digest_is_canonical_and_unicode_safe():
    assert canonical_digest({"b": "冥想", "a": 1}) == canonical_digest({"a": 1, "b": "冥想"})


def test_cosyvoice_uses_ssml_only_up_to_ten_seconds():
    plan = {
        "segments": [
            {"text": "吸气", "pause_strategy": "silence", "pause_after_ms": 5000},
            {"text": "呼气", "pause_strategy": "silence", "pause_after_ms": 10000},
            {"text": "观察", "pause_strategy": "silence", "pause_after_ms": 20000},
        ]
    }
    capabilities = get_tts_capabilities("aliyun", "cosyvoice-v3-flash", "longanyang")
    segments = build_speech_segments(plan, capabilities)
    assert len(segments) == 1
    assert segments[0].enable_ssml is True
    assert '<break time="5000ms"/>' in segments[0].text
    assert '<break time="10000ms"/>' in segments[0].text
    assert "20000ms" not in segments[0].text
    assert segments[0].pause_after_ms == 20000


def test_qwen_never_generates_ssml():
    plan = {
        "segments": [
            {"text": "吸气", "pause_strategy": "silence", "pause_after_ms": 5000},
        ]
    }
    capabilities = get_tts_capabilities("aliyun", "qwen-audio-3.0-tts-plus", "longanlingxin")
    segment = build_speech_segments(plan, capabilities)[0]
    assert segment.enable_ssml is False
    assert "<break" not in segment.text


class RecoveringFakeTTS:
    def __init__(self):
        self.calls: list[int] = []
        self.failed_once = False

    async def synthesize(self, **kwargs):
        index = kwargs["segment_index"]
        self.calls.append(index)
        if index == 1 and not self.failed_once:
            self.failed_once = True
            raise RuntimeError("segment failed")
        return b"valid-wav"


def _render_task() -> AudioTask:
    plan = {
        "version": 1,
        "pause_profile_id": "standard_v1",
        "voice": {},
        "segments": [
            {"text": "第一段", "pause_strategy": "silence", "pause_after_ms": 1000},
            {"text": "第二段", "pause_strategy": "silence", "pause_after_ms": 1000},
        ],
    }
    snapshot = {
        "provider": "aliyun",
        "model": "qwen-audio-3.0-tts-plus",
        "voice_id": "longanlingxin",
        "rate": 0.9,
        "volume": 1,
        "pitch": 1,
        "instruction": "温柔",
        "sample_rate": 48000,
    }
    return AudioTask(
        id=42,
        script_id=1,
        voice_prompt="温柔",
        status="processing",
        render_plan=plan,
        render_plan_digest=canonical_digest(plan),
        tts_snapshot=snapshot,
        tts_snapshot_digest=canonical_digest(snapshot),
    )


async def test_retry_reuses_completed_segments_and_local_stage_failure(tmp_path, monkeypatch):
    fake = RecoveringFakeTTS()
    task = _render_task()
    monkeypatch.setattr(audio_renderer, "probe_audio", lambda path: AudioInfo(1.0, 48000, 1))
    monkeypatch.setattr(
        audio_renderer,
        "create_silence",
        lambda path, *args: path.write_bytes(b"silence") or path,
    )
    monkeypatch.setattr(
        audio_renderer,
        "assemble_wav",
        lambda parts, path, rate: path.write_bytes(b"assembled") or path,
    )
    encode_calls = 0

    def flaky_encode(source, target, rate):
        nonlocal encode_calls
        encode_calls += 1
        if encode_calls == 1:
            raise RuntimeError("encode failed")
        target.write_bytes(b"mp3")
        return target

    monkeypatch.setattr(audio_renderer, "encode_mp3", flaky_encode)
    renderer = AudioRenderer(fake, str(tmp_path))
    with pytest.raises(RuntimeError, match="segment failed"):
        await renderer.render(task)
    assert fake.calls == [0, 1]
    with pytest.raises(RuntimeError, match="encode failed"):
        await renderer.render(task)
    assert fake.calls == [0, 1, 1]
    path, duration = await renderer.render(task)
    assert fake.calls == [0, 1, 1]
    assert path.read_bytes() == b"mp3"
    assert duration == 1.0


async def test_manifest_digest_mismatch_refuses_cache(tmp_path):
    task = _render_task()
    directory = tmp_path / "work" / "42"
    directory.mkdir(parents=True)
    (directory / "manifest.json").write_text(
        '{"task_id":42,"render_plan_digest":"sha256:other",'
        '"tts_snapshot_digest":"sha256:other","segments":[]}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="manifest"):
        await AudioRenderer(RecoveringFakeTTS(), str(tmp_path)).render(task)
