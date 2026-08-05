from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: str = "deepseek"
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = None


class TTSConfig(BaseModel):
    provider: str = "volcano"
    api_key: str = ""
    secret_key: str = ""
    voice_id: str = ""
    speed: float = Field(default=1.0, ge=0.5, le=2)
    volume: float = Field(default=1.0, ge=0, le=2)
    output_format: str = "mp3"


class DifyConfig(BaseModel):
    base_url: str = "http://localhost/v1"
    script_app_key: str = ""
    audio_app_key: str = ""


class GeneralConfig(BaseModel):
    language: str = "zh"
    theme: str = "light"
    audio_output_dir: str = "./data/audio"


class SettingSchema(BaseModel):
    llm_config: LLMConfig
    tts_config: TTSConfig
    dify_config: DifyConfig
    general_config: GeneralConfig
