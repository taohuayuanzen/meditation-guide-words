from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any


class MusicServiceError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


@dataclass(frozen=True)
class MusicGenerationResult:
    request_id: str
    audio_id: str | None
    audio_url: str
    expires_at: datetime | None
    duration_seconds: int
    sample_rate: int | None
    channels: int | None
    source_format: str = "wav"
    estimated_cost: float | None = None


async def generate_music(
    provider: str,
    model: str,
    config: Mapping[str, Any],
    prompt: str,
) -> MusicGenerationResult:
    if provider == "minimax" and model == "music-3.0":
        from app.services.music_minimax import generate_music as generate_minimax

        return await generate_minimax(config, prompt)
    if provider == "aliyun" and model == "fun-music-v1":
        from app.services.music_aliyun import generate_music as generate_aliyun

        return await generate_aliyun(config, prompt)
    raise MusicServiceError(
        "MUSIC_PROVIDER_UNSUPPORTED",
        f"不支持的音乐供应商和模型组合：{provider}/{model}",
    )
