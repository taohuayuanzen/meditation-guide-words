import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.config import settings


class MusicProcessingError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class AudioInfo:
    duration_seconds: float
    sample_rate: int
    channels: int


def probe_audio(path: str | Path) -> AudioInfo:
    file_path = Path(path)
    if not file_path.is_file() or file_path.stat().st_size <= 0:
        raise MusicProcessingError("MUSIC_SOURCE_INVALID", "音乐文件不存在或为空")
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=sample_rate,channels:format=duration",
        "-of",
        "json",
        str(file_path),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=settings.ffprobe_timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise MusicProcessingError("FFPROBE_UNAVAILABLE", "未找到 ffprobe") from exc
    except subprocess.TimeoutExpired as exc:
        raise MusicProcessingError("FFPROBE_TIMEOUT", "音频探测超时") from exc
    if result.returncode != 0:
        raise MusicProcessingError("MUSIC_SOURCE_INVALID", "音乐文件损坏或无法读取")
    try:
        payload = json.loads(result.stdout)
        streams = payload.get("streams") or []
        if not streams:
            raise ValueError("missing audio stream")
        stream = streams[0]
        duration = float(payload["format"]["duration"])
        sample_rate = int(stream["sample_rate"])
        channels = int(stream["channels"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise MusicProcessingError("MUSIC_SOURCE_INVALID", "文件不包含有效音频流") from exc
    if duration <= 0 or sample_rate <= 0 or channels <= 0:
        raise MusicProcessingError("MUSIC_SOURCE_INVALID", "音频参数无效")
    return AudioInfo(duration_seconds=duration, sample_rate=sample_rate, channels=channels)


def _run_ffmpeg(command: list[str]) -> None:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=settings.ffmpeg_timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise MusicProcessingError("FFMPEG_UNAVAILABLE", "未找到 ffmpeg") from exc
    except subprocess.TimeoutExpired as exc:
        raise MusicProcessingError("FFMPEG_TIMEOUT", "音乐时长处理超时") from exc
    if result.returncode != 0:
        raise MusicProcessingError("FFMPEG_FAILED", "音乐时长处理失败")


def _fade_lengths(target_seconds: float) -> tuple[float, float]:
    fade_in = min(3.0, target_seconds / 3)
    fade_out = min(8.0, target_seconds / 3)
    if fade_in + fade_out > target_seconds:
        scale = target_seconds / (fade_in + fade_out)
        fade_in *= scale
        fade_out *= scale
    return fade_in, fade_out


def _create_loop_unit(source: Path, loop_path: Path, info: AudioInfo) -> None:
    crossfade = min(4.0, info.duration_seconds / 3)
    period = info.duration_seconds - crossfade
    if crossfade <= 0.01 or period <= crossfade:
        raise MusicProcessingError("MUSIC_SOURCE_TOO_SHORT", "源音乐过短，无法安全循环")
    filter_graph = (
        "[0:a]asplit=3[headsrc][tailsrc][middlesrc];"
        f"[headsrc]atrim=0:{crossfade:.6f},asetpts=PTS-STARTPTS,"
        f"afade=t=in:st=0:d={crossfade:.6f}[head];"
        f"[tailsrc]atrim={period:.6f}:{info.duration_seconds:.6f},"
        f"asetpts=PTS-STARTPTS,afade=t=out:st=0:d={crossfade:.6f}[tail];"
        "[tail][head]amix=inputs=2:duration=longest:normalize=0[seam];"
        f"[middlesrc]atrim={crossfade:.6f}:{period:.6f},"
        "asetpts=PTS-STARTPTS[middle];"
        "[seam][middle]concat=n=2:v=0:a=1[loop]"
    )
    _run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(source),
            "-filter_complex",
            filter_graph,
            "-map",
            "[loop]",
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            str(loop_path),
        ]
    )


def process_music(
    source_path: str | Path,
    final_path: str | Path,
    target_duration_seconds: int,
) -> tuple[AudioInfo, AudioInfo]:
    if not 60 <= target_duration_seconds <= 3600:
        raise MusicProcessingError("MUSIC_DURATION_INVALID", "目标时长必须为 60～3600 秒")
    source = Path(source_path)
    final = Path(final_path)
    part = final.with_suffix(final.suffix + ".part")
    loop_path = final.with_suffix(".loop.part.wav")
    final.parent.mkdir(parents=True, exist_ok=True)
    source_info = probe_audio(source)
    fade_in, fade_out = _fade_lengths(target_duration_seconds)
    fade_filter = (
        f"atrim=duration={target_duration_seconds},asetpts=PTS-STARTPTS,"
        f"afade=t=in:st=0:d={fade_in:.6f},"
        f"afade=t=out:st={target_duration_seconds - fade_out:.6f}:d={fade_out:.6f}"
    )
    try:
        input_args: list[str]
        if source_info.duration_seconds < target_duration_seconds:
            _create_loop_unit(source, loop_path, source_info)
            input_args = ["-stream_loop", "-1", "-i", str(loop_path)]
        else:
            input_args = ["-i", str(source)]
        _run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                *input_args,
                "-af",
                fade_filter,
                "-t",
                str(target_duration_seconds),
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
                "-f",
                "mp3",
                str(part),
            ]
        )
        final_info = probe_audio(part)
        if abs(final_info.duration_seconds - target_duration_seconds) > 1:
            raise MusicProcessingError("MUSIC_DURATION_MISMATCH", "最终音乐时长校验失败")
        os.replace(part, final)
        return source_info, final_info
    finally:
        part.unlink(missing_ok=True)
        loop_path.unlink(missing_ok=True)
