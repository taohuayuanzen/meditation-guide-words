import json
import subprocess

import pytest

from app.services.music_postprocessor import MusicProcessingError, probe_audio, process_music


def _probe_result(duration=10.0, sample_rate=48000, channels=2):
    return subprocess.CompletedProcess(
        [],
        0,
        stdout=json.dumps(
            {
                "streams": [{"sample_rate": str(sample_rate), "channels": channels}],
                "format": {"duration": str(duration)},
            }
        ),
        stderr="",
    )


def test_probe_audio_reads_real_metadata(tmp_path, monkeypatch):
    source = tmp_path / "source.wav"
    source.write_bytes(b"wav")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: _probe_result(12.4))
    info = probe_audio(source)
    assert info.duration_seconds == 12.4
    assert info.sample_rate == 48000
    assert info.channels == 2


def test_probe_rejects_file_without_audio_stream(tmp_path, monkeypatch):
    source = tmp_path / "source.wav"
    source.write_bytes(b"invalid")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            [], 0, stdout='{"streams": [], "format": {"duration": "1"}}', stderr=""
        ),
    )
    with pytest.raises(MusicProcessingError, match="有效音频流"):
        probe_audio(source)


def test_short_source_builds_loop_and_cleans_temporary_files(tmp_path, monkeypatch):
    source = tmp_path / "source.wav"
    final = tmp_path / "final.mp3"
    source.write_bytes(b"wav")
    commands = []
    probe_calls = 0

    def fake_run(command, **kwargs):
        nonlocal probe_calls
        commands.append(command)
        if command[0] == "ffprobe":
            probe_calls += 1
            duration = 30 if probe_calls == 1 else 60
            return _probe_result(duration)
        output = command[-1]
        with open(output, "wb") as file:
            file.write(b"generated")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    source_info, final_info = process_music(source, final, 60)
    assert source_info.duration_seconds == 30
    assert final_info.duration_seconds == 60
    assert final.read_bytes() == b"generated"
    assert any("-stream_loop" in command for command in commands)
    filter_graph = next(
        command[command.index("-filter_complex") + 1]
        for command in commands
        if "-filter_complex" in command
    )
    assert "atrim=0:4.000000" in filter_graph
    assert not (tmp_path / "final.loop.part.wav").exists()
    assert not (tmp_path / "final.mp3.part").exists()


def test_ffmpeg_failure_cleans_part_and_keeps_source(tmp_path, monkeypatch):
    source = tmp_path / "source.wav"
    final = tmp_path / "final.mp3"
    source.write_bytes(b"wav")

    def fake_run(command, **kwargs):
        if command[0] == "ffprobe":
            return _probe_result(120)
        final.with_suffix(".mp3.part").write_bytes(b"partial")
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="failed")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(MusicProcessingError, match="时长处理失败"):
        process_music(source, final, 60)
    assert source.exists()
    assert not final.with_suffix(".mp3.part").exists()
