from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/meditation.db"
    audio_output_dir: str = "./data/audio"
    dify_base_url: str = "http://localhost/v1"
    worker_concurrency: int = 2

    class Config:
        env_file = ".env"


settings = Settings()
