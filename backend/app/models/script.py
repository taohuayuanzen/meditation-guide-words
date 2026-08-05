from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.utils.time_utils import utc_now


class Script(Base):
    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str]
    content: Mapped[str]
    session_id: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)
