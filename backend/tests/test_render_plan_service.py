import copy

import pytest

from app.schemas.audio_render_plan import AudioRenderPlan
from app.schemas.script_plan import ScriptPlan
from app.services.render_plan_service import (
    _strip_json_fence,
    estimate_duration,
    validate_render_plan,
)

SCRIPT_PLAN = ScriptPlan.model_validate(
    {
        "version": 1,
        "target_duration_seconds": 60,
        "blocks": [
            {"id": "b1", "text": "现在，感受呼吸。", "pause_after": {"kind": "short"}},
            {
                "id": "b2",
                "text": "安静地观察身体。",
                "pause_after": {"kind": "observe", "suggested_seconds": 10},
            },
        ],
    }
)

RAW_PLAN = {
    "version": 1,
    "pause_profile_id": "standard_v1",
    "voice": {
        "voice_id": "longanlingxin",
        "rate": 0.9,
        "volume": 1.0,
        "pitch": 1.0,
        "instruction": "温柔、平静、语速稍慢",
    },
    "segments": [
        {
            "id": "b1",
            "text": "现在，感受呼吸。",
            "pause_after_ms": 700,
            "pause_kind": "short",
            "pause_strategy": "natural",
        },
        {
            "id": "b2",
            "text": "安静地观察身体。",
            "pause_after_ms": 10000,
            "pause_kind": "observe",
            "pause_strategy": "silence",
        },
    ],
}

CONTEXT = {"allowed_voices": ["longanlingxin"]}


def test_json_cleanup_accepts_complete_leading_think_block():
    answer = '<think>内部推理，不属于业务数据</think>\n```json\n{"version": 1}\n```'
    assert _strip_json_fence(answer) == '{"version": 1}'


def test_json_cleanup_rejects_unclosed_think_block():
    with pytest.raises(ValueError, match="思考内容未完整结束"):
        _strip_json_fence("<think>尚未结束")


def test_render_plan_is_validated_and_estimated_with_both_pause_budgets():
    plan = validate_render_plan(RAW_PLAN, SCRIPT_PLAN, "standard_v1", CONTEXT)
    estimate = estimate_duration(plan, SCRIPT_PLAN)
    assert estimate.estimated_natural_pause_seconds > 0
    assert estimate.deterministic_pause_seconds == 10
    assert estimate.estimated_total_seconds > estimate.estimated_speech_seconds


@pytest.mark.parametrize("mutation", ["text", "order", "voice", "strategy", "duration"])
def test_render_plan_cannot_change_trusted_fields(mutation):
    raw = copy.deepcopy(RAW_PLAN)
    if mutation == "text":
        raw["segments"][0]["text"] = "被改写"
    elif mutation == "order":
        raw["segments"].reverse()
    elif mutation == "voice":
        raw["voice"]["voice_id"] = "unknown"
    elif mutation == "strategy":
        raw["segments"][0]["pause_strategy"] = "silence"
    else:
        raw["segments"][1]["pause_after_ms"] = 9000
    with pytest.raises(ValueError):
        validate_render_plan(raw, SCRIPT_PLAN, "standard_v1", CONTEXT)


def test_render_plan_rejects_ssml_and_voice_ranges():
    raw = copy.deepcopy(RAW_PLAN)
    raw["segments"][0]["text"] = "<break time='1s'/>"
    with pytest.raises(ValueError):
        AudioRenderPlan.model_validate(raw)
    raw = copy.deepcopy(RAW_PLAN)
    raw["voice"]["rate"] = 1.2
    with pytest.raises(ValueError):
        AudioRenderPlan.model_validate(raw)
