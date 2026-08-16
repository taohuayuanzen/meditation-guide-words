import pytest

from app.schemas.script_plan import SemanticPause
from app.services.pause_profiles import PAUSE_PROFILES, get_pause_profile, quantify_pause


def test_pause_profiles_have_stable_v1_values():
    assert list(PAUSE_PROFILES) == ["gentle_v1", "standard_v1", "deep_v1"]
    assert get_pause_profile("standard_v1").durations["paragraph"] == 1800
    assert get_pause_profile("deep_v1").durations["ending"] == 8000


def test_suggested_seconds_uses_profile_factor():
    pause = SemanticPause(kind="observe", suggested_seconds=20)
    assert quantify_pause(pause, get_pause_profile("gentle_v1")) == 15_000
    assert quantify_pause(pause, get_pause_profile("standard_v1")) == 20_000
    assert quantify_pause(pause, get_pause_profile("deep_v1")) == 27_000


def test_breath_count_is_multiplied_and_range_is_enforced():
    pause = SemanticPause(kind="breath", count=3)
    assert quantify_pause(pause, get_pause_profile("standard_v1")) == 15_000
    with pytest.raises(ValueError, match="60000"):
        quantify_pause(SemanticPause(kind="breath", count=10), get_pause_profile("deep_v1"))


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "invented"},
        {"kind": "breath", "count": 0},
        {"kind": "observe", "suggested_seconds": 4},
        {"kind": "paragraph", "count": 1},
    ],
)
def test_invalid_semantic_pause_is_rejected(payload):
    with pytest.raises(ValueError):
        SemanticPause.model_validate(payload)
