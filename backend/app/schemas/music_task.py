from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MusicTaskCreate(BaseModel):
    prompt: str = ""
    effective_prompt: str = Field(min_length=1, max_length=2000)
    preset_params: dict[str, Any] = Field(default_factory=dict)
    target_duration_seconds: int = Field(ge=60, le=3600)

    @field_validator("effective_prompt")
    @classmethod
    def validate_effective_prompt(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("effective_prompt 不能为空")
        return value


class MusicTaskRetry(BaseModel):
    confirm_regenerate: bool = False


class MusicTaskResponse(BaseModel):
    id: int
    prompt: str
    effective_prompt: str
    preset_params: dict[str, Any]
    provider: str
    model: str
    source_format: str
    status: str
    stage: str
    retry_count: int
    download_retry_count: int
    request_id: str | None = None
    remote_audio_id: str | None = None
    remote_url_expires_at: datetime | None = None
    source_duration_seconds: int | None = None
    target_duration_seconds: int
    final_duration_seconds: int | None = None
    sample_rate: int | None = None
    channels: int | None = None
    source_file_path: str | None = None
    file_path: str | None = None
    output_format: str
    is_ai_generated: bool
    watermark_enabled: bool
    estimated_cost: float | None = None
    error_code: str | None = None
    error_msg: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MusicCapabilitiesResponse(BaseModel):
    ffmpeg_available: bool
    ffprobe_available: bool
    music_processing_available: bool


class MusicDownloadItem(BaseModel):
    kind: str
    format: str
    label: str
    size: int
    duration_seconds: float | int | None = None
    download_url: str


class MusicDownloadsResponse(BaseModel):
    items: list[MusicDownloadItem]
