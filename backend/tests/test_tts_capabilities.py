import pytest

from app.services.tts_capabilities import get_tts_capabilities, validate_snapshot_capabilities


def test_qwen_never_enables_ssml():
    capabilities = get_tts_capabilities("aliyun", "qwen-audio-3.0-tts-plus")
    assert capabilities.supports_instruction
    assert not capabilities.supports_ssml


def test_unsupported_pitch_is_rejected_in_snapshot():
    with pytest.raises(ValueError, match="pitch"):
        validate_snapshot_capabilities(
            {
                "provider": "aliyun",
                "model": "qwen-audio-3.0-tts-plus",
                "voice_id": "longanlingxin",
                "pitch": 1.2,
            }
        )


def test_cosyvoice_capability_has_ten_second_ssml_limit():
    capabilities = get_tts_capabilities("aliyun", "cosyvoice-v3-flash")
    assert capabilities.supports_ssml
    assert capabilities.max_ssml_break_ms == 10_000
