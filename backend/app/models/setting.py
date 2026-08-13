from datetime import datetime

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.utils.time_utils import utc_now


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1, autoincrement=False)
    llm_config: Mapped[dict] = mapped_column(JSON, default=dict)
    tts_config: Mapped[dict] = mapped_column(JSON, default=dict)
    dify_config: Mapped[dict] = mapped_column(JSON, default=dict)
    general_config: Mapped[dict] = mapped_column(JSON, default=dict)
    music_config: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now)
