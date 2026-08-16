import json
import os
import subprocess
from pathlib import Path

from app.config import settings
from app.services.music_postprocessor import AudioInfo


class AudioProcessingError(RuntimeError):
    pass


def _run(command: list[str], timeout: float) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise AudioProcessingError(f"音频工具不可用或超时: {command[0]}") from exc
    if result.returncode:
        raise AudioProcessingError(f"音频处理失败: {command[0]}")
    return result


def probe_audio(path: str | Path) -> AudioInfo:
    file_path = Path(path)
    if not file_path.is_file() or file_path.stat().st_size == 0:
        raise AudioProcessingError("音频文件不存在或为空")
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate,channels,codec_name:format=duration",
            "-of",
            "json",
            str(file_path),
        ],
        settings.ffprobe_timeout_seconds,
    )
    try:
        payload = json.loads(result.stdout)
        stream = payload["streams"][0]
        info = AudioInfo(
            float(payload["format"]["duration"]),
            int(stream["sample_rate"]),
            int(stream["channels"]),
        )
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AudioProcessingError("音频探测结果无效") from exc
    if info.duration_seconds <= 0:
        raise AudioProcessingError("音频时长无效")
    return info


def create_silence(
    path: str | Path, duration_ms: int, sample_rate: int = 48000, channels: int = 1
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    layout = "mono" if channels == 1 else "stereo"
    _run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r={sample_rate}:cl={layout}",
            "-t",
            f"{duration_ms / 1000:.3f}",
            "-c:a",
            "pcm_s16le",
            str(target),
        ],
        settings.ffmpeg_timeout_seconds,
    )
    return target


def assemble_wav(parts: list[Path], assembled: str | Path, sample_rate: int = 48000) -> Path:
    if not parts:
        raise AudioProcessingError("没有可拼接的音频段")
    expected_channels: int | None = None
    for part in parts:
        info = probe_audio(part)
        if info.sample_rate != sample_rate:
            raise AudioProcessingError("中间音频采样率不一致")
        if expected_channels is None:
            expected_channels = info.channels
        elif info.channels != expected_channels:
            raise AudioProcessingError("中间音频声道数不一致")
    assembled_path = Path(assembled)
    assembled_path.parent.mkdir(parents=True, exist_ok=True)
    output_part = assembled_path.with_suffix(".wav.part")
    manifest = assembled_path.parent / f".{assembled_path.stem}.concat.txt"
    manifest.write_text(
        "".join(f"file '{p.resolve().as_posix()}'\n" for p in parts), encoding="utf-8"
    )
    try:
        _run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(manifest),
                "-ar",
                str(sample_rate),
                "-c:a",
                "pcm_s16le",
                "-f",
                "wav",
                str(output_part),
            ],
            settings.ffmpeg_timeout_seconds,
        )
        probe_audio(output_part)
        os.replace(output_part, assembled_path)
        return assembled_path
    finally:
        manifest.unlink(missing_ok=True)
        output_part.unlink(missing_ok=True)


def encode_mp3(source: str | Path, final: str | Path, sample_rate: int = 48000) -> Path:
    source_path = Path(source)
    probe_audio(source_path)
    final_path = Path(final)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    output_part = final_path.with_suffix(".mp3.part")
    try:
        _run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(source_path),
                "-ar",
                str(sample_rate),
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
                "-f",
                "mp3",
                str(output_part),
            ],
            settings.ffmpeg_timeout_seconds,
        )
        probe_audio(output_part)
        os.replace(output_part, final_path)
        return final_path
    finally:
        output_part.unlink(missing_ok=True)


def assemble_audio(parts: list[Path], final: str | Path, sample_rate: int = 48000) -> AudioInfo:
    final_path = Path(final)
    assembled = final_path.with_suffix(".assembled.part.wav")
    try:
        assemble_wav(parts, assembled, sample_rate)
        encode_mp3(assembled, final_path, sample_rate)
        return probe_audio(final_path)
    finally:
        assembled.unlink(missing_ok=True)
