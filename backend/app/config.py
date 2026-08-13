import logging
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


def setup_logging() -> None:
    """根据 LOG_LEVEL 环境变量配置根日志器。"""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/meditation.db"
    audio_output_dir: str = "./data/audio"
    music_source_dir: str = "./data/music/source"
    music_final_dir: str = "./data/music/final"
    ffprobe_timeout_seconds: float = 15.0
    ffmpeg_timeout_seconds: float = 900.0
    dify_base_url: str = "http://localhost/v1"
    dify_script_app_key: str = ""
    dify_audio_app_key: str = ""
    worker_concurrency: int = 2

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
