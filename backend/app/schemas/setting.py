from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator


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
    appid: str = ""
    cluster: str = "volcano_tts"
    voice_id: str = ""
    speed: float = Field(default=1.0, ge=0.5, le=2)
    volume: float = Field(default=1.0, ge=0, le=2)
    output_format: str = "mp3"
    model: str = "qwen-audio-3.0-tts-plus"
    base_url: str = "https://dashscope.aliyuncs.com/api/v1"


class DifyConfig(BaseModel):
    base_url: str = "http://localhost/v1"
    script_app_key: str = ""
    audio_app_key: str = ""


class GeneralConfig(BaseModel):
    language: str = "zh"
    theme: str = "light"
    audio_output_dir: str = "./data/audio"


def _validate_music_base_url(value: str, *, allow_empty: bool) -> str:
    value = value.strip().rstrip("/")
    if not value and allow_empty:
        return ""
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("音乐 Base URL 必须是有效的 HTTP(S) 地址")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("音乐 Base URL 不能包含凭证、查询参数或片段")
    return value


class AliyunMusicConfig(BaseModel):
    api_key: str = ""
    workspace_id: str = ""
    base_url: str = ""
    model: Literal["fun-music-v1"] = "fun-music-v1"
    source_format: Literal["wav"] = "wav"

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return _validate_music_base_url(value, allow_empty=True)


class MiniMaxMusicConfig(BaseModel):
    api_key: str = ""
    base_url: str = "https://api.minimaxi.com/v1"
    model: Literal["music-3.0"] = "music-3.0"
    source_format: Literal["mp3"] = "mp3"

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return _validate_music_base_url(value, allow_empty=False)


class MusicConfig(BaseModel):
    provider: Literal["minimax", "aliyun"] = "minimax"
    output_format: Literal["mp3"] = "mp3"
    enable_aigc_watermark: Literal[False] = False
    worker_concurrency: int = Field(default=1, ge=1, le=8)
    aliyun: AliyunMusicConfig = Field(default_factory=AliyunMusicConfig)
    minimax: MiniMaxMusicConfig = Field(default_factory=MiniMaxMusicConfig)

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_flat_config(cls, value):
        if not isinstance(value, dict) or "aliyun" in value or "minimax" in value:
            return value
        legacy_keys = {"api_key", "workspace_id", "base_url", "model", "source_format"}
        if not legacy_keys.intersection(value):
            return value
        migrated = {key: item for key, item in value.items() if key not in legacy_keys}
        migrated["provider"] = "minimax"
        migrated["aliyun"] = {key: value[key] for key in legacy_keys if key in value}
        migrated["minimax"] = MiniMaxMusicConfig().model_dump()
        return migrated


class SettingSchema(BaseModel):
    llm_config: LLMConfig
    tts_config: TTSConfig
    dify_config: DifyConfig
    general_config: GeneralConfig
    music_config: MusicConfig = Field(default_factory=MusicConfig)
