from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.script_plan import PauseKind, validate_plain_text


class PauseProfile(BaseModel):
    id: str
    version: Literal[1] = 1
    durations: dict[str, int]
    suggested_seconds_factor: float

    model_config = ConfigDict(extra="forbid", frozen=True)

    def public_dict(self) -> dict:
        return self.model_dump()


class VoiceRenderParams(BaseModel):
    voice_id: str = Field(min_length=1, max_length=100)
    rate: float = Field(ge=0.75, le=1.05)
    volume: float = Field(ge=0, le=2)
    pitch: float = Field(ge=0.5, le=2)
    instruction: str = Field(min_length=1, max_length=200)

    model_config = ConfigDict(extra="forbid")

    @field_validator("instruction")
    @classmethod
    def instruction_plain_text_only(cls, value: str) -> str:
        return validate_plain_text(value)


class AudioRenderSegment(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    text: str = Field(max_length=5000)
    pause_after_ms: int = Field(ge=0, le=60_000)
    pause_kind: PauseKind
    pause_strategy: Literal["natural", "silence"]

    model_config = ConfigDict(extra="forbid")

    @field_validator("text")
    @classmethod
    def plain_text_only(cls, value: str) -> str:
        return validate_plain_text(value)


class AudioRenderPlan(BaseModel):
    version: Literal[1] = 1
    pause_profile_id: str
    voice: VoiceRenderParams
    segments: list[AudioRenderSegment] = Field(min_length=1, max_length=500)

    model_config = ConfigDict(extra="forbid")


class DurationEstimate(BaseModel):
    estimated_speech_seconds: int
    estimated_natural_pause_seconds: int
    deterministic_pause_seconds: int
    estimated_total_seconds: int
    target_duration_seconds: int
    duration_delta_seconds: int
    estimation_version: Literal["zh_v1"] = "zh_v1"


class RenderPlanPreviewRequest(BaseModel):
    script_id: int = Field(gt=0)
    pause_profile_id: str = "standard_v1"
    voice_prompt: str = Field(min_length=1, max_length=500)


class RenderPlanPreviewResponse(BaseModel):
    render_plan: AudioRenderPlan
    render_plan_digest: str
    preview_digest: str
    estimate: DurationEstimate
