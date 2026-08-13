from datetime import datetime

from sqlalchemy import JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.utils.time_utils import utc_now


class MusicTask(Base):
    __tablename__ = "music_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    prompt: Mapped[str] = mapped_column(Text)
    effective_prompt: Mapped[str] = mapped_column(Text)
    preset_params: Mapped[dict] = mapped_column(JSON, default=dict)
    provider: Mapped[str] = mapped_column(default="aliyun")
    model: Mapped[str]
    source_format: Mapped[str] = mapped_column(default="wav")
    status: Mapped[str] = mapped_column(default="pending", index=True)
    stage: Mapped[str] = mapped_column(default="generating")
    retry_count: Mapped[int] = mapped_column(default=0)
    download_retry_count: Mapped[int] = mapped_column(default=0)
    request_id: Mapped[str | None]
    remote_audio_id: Mapped[str | None]
    remote_audio_url: Mapped[str | None] = mapped_column(Text)
    remote_url_expires_at: Mapped[datetime | None]
    source_duration_seconds: Mapped[int | None]
    target_duration_seconds: Mapped[int]
    final_duration_seconds: Mapped[int | None]
    sample_rate: Mapped[int | None]
    channels: Mapped[int | None]
    source_file_path: Mapped[str | None]
    file_path: Mapped[str | None]
    output_format: Mapped[str] = mapped_column(default="mp3")
    is_ai_generated: Mapped[bool] = mapped_column(default=True)
    watermark_enabled: Mapped[bool] = mapped_column(default=False)
    estimated_cost: Mapped[float | None]
    error_code: Mapped[str | None]
    error_msg: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, index=True)
    completed_at: Mapped[datetime | None]
