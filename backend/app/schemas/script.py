from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.schemas.script_plan import ScriptPlan, script_plan_content, validate_plain_text


class ScriptCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str | None = Field(default=None, max_length=20_000)
    script_plan: ScriptPlan | None = None
    session_id: str | None = None

    @field_validator("content")
    @classmethod
    def validate_legacy_content(cls, value: str | None) -> str | None:
        return validate_plain_text(value) if value is not None else None

    @model_validator(mode="after")
    def validate_content_source(self):
        if self.script_plan is None:
            if not self.content or not self.content.strip():
                raise ValueError("旧格式脚本必须提供 content")
            return self
        generated = script_plan_content(self.script_plan)
        if self.content is not None and self.content.strip() != generated:
            raise ValueError("content 必须与 script_plan.blocks 一致")
        return self


class ScriptResponse(BaseModel):
    id: int
    title: str
    content: str
    script_plan: ScriptPlan | None = None
    session_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def pause_capable(self) -> bool:
        return self.script_plan is not None and self.script_plan.version == 1

    @computed_field
    @property
    def target_duration_seconds(self) -> int | None:
        return self.script_plan.target_duration_seconds if self.script_plan else None


class ScriptListResponse(BaseModel):
    items: list[ScriptResponse]
    total: int
