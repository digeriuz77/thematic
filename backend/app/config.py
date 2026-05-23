from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Thematic Analysis Toolkit"
    debug: bool = False

    database_url: str = "sqlite:///./thematic_analysis.db"
    redis_url: str = "redis://localhost:6379/0"

    anthropic_api_key: str = ""
    claude_model: str = "claude-3-5-sonnet-20241022"

    uploads_dir: str = "./data/uploads"
    reports_dir: str = "./data/reports"
    maps_dir: str = "./data/maps"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
