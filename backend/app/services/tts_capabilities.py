from dataclasses import dataclass


@dataclass(frozen=True)
class TTSCapabilities:
    supports_instruction: bool
    supports_ssml: bool
    supports_pitch: bool
    max_ssml_break_ms: int = 0
    supported_voices: tuple[str, ...] = ()


_CAPABILITIES = {
    "qwen-audio-3.0-tts-plus": TTSCapabilities(
        True, False, False, supported_voices=("longanlingxin", "longanlufeng")
    ),
    "qwen-audio-3.0-tts-flash": TTSCapabilities(
        True,
        False,
        False,
        supported_voices=(
            "longanfengyue",
            "longanyuanfei",
            "longanlingxi",
            "longanxiaoxin",
            "longanhuan_v3.6",
            "longjielidou_v3.6",
            "longpaopao_v3.6",
            "longhuohuo_v3.6",
            "longchuanshu_v3.6",
            "loongmary",
            "loongeva_v3.6",
            "loongjohn",
        ),
    ),
    "cosyvoice-v3-flash": TTSCapabilities(
        False,
        True,
        True,
        10_000,
        supported_voices=("longanyang", "longanhuan_v3"),
    ),
}


def get_tts_capabilities(provider: str, model: str, voice_id: str = "") -> TTSCapabilities:
    if provider != "aliyun":
        return TTSCapabilities(False, False, False)
    capabilities = _CAPABILITIES.get(model, TTSCapabilities(False, False, False))
    if voice_id and capabilities.supported_voices and voice_id not in capabilities.supported_voices:
        return TTSCapabilities(
            capabilities.supports_instruction, False, capabilities.supports_pitch
        )
    return capabilities


def validate_snapshot_capabilities(snapshot: dict) -> None:
    capabilities = get_tts_capabilities(
        snapshot.get("provider", ""), snapshot.get("model", ""), snapshot.get("voice_id", "")
    )
    pitch = float(snapshot.get("pitch", 1.0))
    if (
        capabilities.supported_voices
        and snapshot.get("voice_id") not in capabilities.supported_voices
    ):
        raise ValueError("当前 TTS 模型与音色组合不受支持")
    if pitch != 1.0 and not capabilities.supports_pitch:
        raise ValueError("当前 TTS 模型不支持 pitch，不能保证任务快照一致性")
    if snapshot.get("instruction") and not capabilities.supports_instruction:
        raise ValueError("当前 TTS 模型不支持 instruction，不能保证任务快照一致性")
