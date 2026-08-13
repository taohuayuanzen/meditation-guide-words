import subprocess

from app.services import media_capabilities


def test_capabilities_available(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0),
    )
    media_capabilities.get_media_capabilities.cache_clear()
    result = media_capabilities.get_media_capabilities()
    assert result.ffmpeg_available is True
    assert result.ffprobe_available is True
    assert result.music_processing_available is True


def test_capabilities_missing(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", missing)
    media_capabilities.get_media_capabilities.cache_clear()
    result = media_capabilities.get_media_capabilities()
    assert result.ffmpeg_available is False
    assert result.ffprobe_available is False
    assert result.music_processing_available is False
