import subprocess
from dataclasses import asdict, dataclass
from functools import lru_cache


@dataclass(frozen=True)
class MediaCapabilities:
    ffmpeg_available: bool
    ffprobe_available: bool

    @property
    def music_processing_available(self) -> bool:
        return self.ffmpeg_available and self.ffprobe_available

    def model_dump(self) -> dict[str, bool]:
        return {
            **asdict(self),
            "music_processing_available": self.music_processing_available,
        }


def _command_available(command: str) -> bool:
    try:
        result = subprocess.run(
            [command, "-version"],
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


@lru_cache(maxsize=1)
def get_media_capabilities() -> MediaCapabilities:
    return MediaCapabilities(
        ffmpeg_available=_command_available("ffmpeg"),
        ffprobe_available=_command_available("ffprobe"),
    )
