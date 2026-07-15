from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SDIE_", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://sdie:sdie@localhost:5432/sdie"
    redis_url: str = "redis://localhost:6379/0"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    cors_allow_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
