from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AudioTaskCreate(BaseModel):
    script_id: int
    voice_prompt: str
    tts_params: dict | None = None


class AudioTaskResponse(BaseModel):
    id: int
    script_id: int
    voice_prompt: str
    tts_params: dict | None = None
    status: str
    retry_count: int = 0
    file_path: str | None = None
    error_msg: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
