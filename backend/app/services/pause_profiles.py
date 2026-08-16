from app.schemas.audio_render_plan import PauseProfile
from app.schemas.script_plan import SemanticPause

_BASE = {
    "gentle_v1": (
        {
            "short": 500,
            "paragraph": 1200,
            "breath": 4000,
            "observe": 8000,
            "practice": 10000,
            "transition": 1800,
            "ending": 3000,
        },
        0.75,
    ),
    "standard_v1": (
        {
            "short": 700,
            "paragraph": 1800,
            "breath": 5000,
            "observe": 15000,
            "practice": 18000,
            "transition": 2500,
            "ending": 5000,
        },
        1.0,
    ),
    "deep_v1": (
        {
            "short": 900,
            "paragraph": 2500,
            "breath": 6500,
            "observe": 25000,
            "practice": 30000,
            "transition": 3500,
            "ending": 8000,
        },
        1.35,
    ),
}

PAUSE_PROFILES = {
    profile_id: PauseProfile(
        id=profile_id,
        version=1,
        durations=durations,
        suggested_seconds_factor=factor,
    )
    for profile_id, (durations, factor) in _BASE.items()
}


def get_pause_profile(profile_id: str) -> PauseProfile:
    try:
        return PAUSE_PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"未知停顿档案: {profile_id}") from exc


def quantify_pause(pause: SemanticPause, profile: PauseProfile) -> int:
    if pause.kind == "none":
        value = 0
    elif pause.kind == "breath":
        value = profile.durations["breath"] * (pause.count or 1)
    elif pause.suggested_seconds is not None:
        value = round(pause.suggested_seconds * 1000 * profile.suggested_seconds_factor)
    else:
        value = profile.durations[pause.kind]
    if not 0 <= value <= 60_000:
        raise ValueError(f"{pause.kind} 量化结果 {value}ms 超出 0～60000ms")
    return value


def pause_strategy(kind: str) -> str:
    return "natural" if kind in {"short", "none"} else "silence"
