from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.audio_render_plan import AudioRenderPlan


class AudioTaskCreate(BaseModel):
    script_id: int
    voice_prompt: str
    tts_params: dict | None = None
    render_plan: AudioRenderPlan | None = None
    render_plan_digest: str | None = None
    preview_digest: str | None = None


class AudioTaskResponse(BaseModel):
    id: int
    script_id: int
    voice_prompt: str
    tts_params: dict | None = None
    render_plan_version: int | None = None
    render_plan_digest: str | None = None
    pause_profile_id: str | None = None
    stage: str | None = None
    completed_segments: int = 0
    total_segments: int | None = None
    estimated_speech_seconds: float | None = None
    estimated_pause_seconds: float | None = None
    estimated_total_seconds: float | None = None
    actual_duration_seconds: float | None = None
    duration_deviation_percent: float | None = None
    provider: str | None = None
    model: str | None = None
    voice_id: str | None = None
    status: str
    retry_count: int = 0
    file_path: str | None = None
    error_msg: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
