from app.services.tts_aliyun import AliyunTTS
from app.services.tts_volcano import VolcanoTTS


def get_tts_service(config: dict):
    provider = config.get("provider", "volcano")
    if provider == "volcano":
        return VolcanoTTS(
            api_key=config.get("api_key", ""),
            secret_key=config.get("secret_key", ""),
            appid=config.get("appid", ""),
            cluster=config.get("cluster", "volcano_tts"),
        )
    if provider == "aliyun":
        return AliyunTTS(
            api_key=config.get("api_key", ""),
            secret_key=config.get("secret_key", ""),
            model=config.get("model", "qwen-audio-3.0-tts-plus"),
            base_url=config.get("base_url", "https://dashscope.aliyuncs.com/api/v1"),
        )
    raise ValueError(f"Unsupported TTS provider: {provider}")
