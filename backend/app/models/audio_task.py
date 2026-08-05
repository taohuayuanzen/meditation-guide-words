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
    status: Mapped[str] = mapped_column(default="pending")
    file_path: Mapped[str | None]
    error_msg: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    completed_at: Mapped[datetime | None]
