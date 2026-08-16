from datetime import datetime

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.utils.time_utils import utc_now


class AudioTask(Base):
    __tablename__ = "audio_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("scripts.id"))
    voice_prompt: Mapped[str]
    tts_params: Mapped[dict | None] = mapped_column(JSON, default=None)
    render_plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    render_plan_version: Mapped[int | None] = mapped_column(nullable=True)
    render_plan_digest: Mapped[str | None] = mapped_column(nullable=True)
    pause_profile_id: Mapped[str | None] = mapped_column(nullable=True)
    tts_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tts_snapshot_digest: Mapped[str | None] = mapped_column(nullable=True)
    estimated_speech_seconds: Mapped[float | None] = mapped_column(nullable=True)
    estimated_pause_seconds: Mapped[float | None] = mapped_column(nullable=True)
    estimated_total_seconds: Mapped[float | None] = mapped_column(nullable=True)
    actual_duration_seconds: Mapped[float | None] = mapped_column(nullable=True)
    stage: Mapped[str | None] = mapped_column(nullable=True)
    completed_segments: Mapped[int] = mapped_column(default=0)
    total_segments: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(default="pending")
    retry_count: Mapped[int] = mapped_column(default=0)
    file_path: Mapped[str | None]
    error_msg: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    completed_at: Mapped[datetime | None]

    @property
    def provider(self) -> str | None:
        return (self.tts_snapshot or {}).get("provider")

    @property
    def model(self) -> str | None:
        return (self.tts_snapshot or {}).get("model")

    @property
    def voice_id(self) -> str | None:
        return (self.tts_snapshot or {}).get("voice_id")

    @property
    def duration_deviation_percent(self) -> float | None:
        if not self.actual_duration_seconds or not self.estimated_total_seconds:
            return None
        return round(
            (self.actual_duration_seconds - self.estimated_total_seconds)
            / self.estimated_total_seconds
            * 100,
            2,
        )
