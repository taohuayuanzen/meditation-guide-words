from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScriptCreate(BaseModel):
    title: str
    content: str
    session_id: str | None = None


class ScriptResponse(BaseModel):
    id: int
    title: str
    content: str
    session_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScriptListResponse(BaseModel):
    items: list[ScriptResponse]
    total: int
