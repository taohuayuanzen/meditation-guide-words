import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PauseKind = Literal[
    "short", "paragraph", "breath", "observe", "practice", "transition", "ending", "none"
]

_TAG_PATTERN = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")


def validate_plain_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("文本不能为空")
    if _TAG_PATTERN.search(value):
        raise ValueError("文本不能包含 HTML、XML 或 SSML 标签")
    return value


class SemanticPause(BaseModel):
    kind: PauseKind
    count: int | None = None
    suggested_seconds: int | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_parameters(self):
        if self.kind == "breath":
            if self.count is None or not 1 <= self.count <= 10:
                raise ValueError("breath.count 必须在 1～10 之间")
            if self.suggested_seconds is not None:
                raise ValueError("breath 不支持 suggested_seconds")
        elif self.kind in {"observe", "practice"}:
            if self.count is not None:
                raise ValueError(f"{self.kind} 不支持 count")
            if self.suggested_seconds is not None and not 5 <= self.suggested_seconds <= 60:
                raise ValueError("suggested_seconds 必须在 5～60 之间")
        elif self.count is not None or self.suggested_seconds is not None:
            raise ValueError(f"{self.kind} 不支持停顿参数")
        return self


class ScriptBlock(BaseModel):
    id: str | None = Field(default=None, min_length=1, max_length=64)
    text: str = Field(max_length=5000)
    pause_after: SemanticPause

    model_config = ConfigDict(extra="forbid")

    @field_validator("text")
    @classmethod
    def plain_text_only(cls, value: str) -> str:
        return validate_plain_text(value)


class ScriptPlan(BaseModel):
    version: Literal[1] = 1
    target_duration_seconds: int = Field(ge=30, le=7200)
    blocks: list[ScriptBlock] = Field(min_length=1, max_length=500)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_blocks(self):
        ids = [block.id for block in self.blocks if block.id is not None]
        if len(ids) != len(set(ids)):
            raise ValueError("block.id 在脚本内必须唯一")
        if sum(len(block.text) for block in self.blocks) > 20_000:
            raise ValueError("脚本总字符数不能超过 20000")
        return self


def normalize_script_plan(plan: ScriptPlan) -> ScriptPlan:
    data = plan.model_dump()
    for index, block in enumerate(data["blocks"], start=1):
        block["id"] = f"b{index}"
    return ScriptPlan.model_validate(data)


def script_plan_content(plan: ScriptPlan) -> str:
    return "\n\n".join(block.text for block in plan.blocks)
