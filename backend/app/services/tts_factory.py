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
        )
    raise ValueError(f"Unsupported TTS provider: {provider}")
