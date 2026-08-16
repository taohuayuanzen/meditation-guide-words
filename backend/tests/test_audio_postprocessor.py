import shutil

import pytest

from app.services.audio_postprocessor import create_silence, probe_audio


@pytest.mark.parametrize("duration_ms", [5000, 10000, 20000, 60000])
def test_silence_has_requested_duration_and_format(tmp_path, duration_ms):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg integration test requires local binaries")
    target = tmp_path / "silence.wav"
    create_silence(target, duration_ms, 48000, 1)
    info = probe_audio(target)
    assert abs(info.duration_seconds - duration_ms / 1000) <= 0.02
    assert info.sample_rate == 48000
    assert info.channels == 1
