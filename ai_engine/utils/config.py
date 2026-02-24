from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    GOOGLE_API_KEY: Optional[str] = None
    BACKEND_URL: str = "http://localhost:8000"
    INTERNAL_API_KEY: str
    ENABLE_MMR_RERANK: bool = False
    ENABLE_DEBUG_ENDPOINTS: bool = False
    ENV: str = "development"

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra env vars


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    if settings.ENV.lower() in {"production", "prod"} and settings.INTERNAL_API_KEY == "dev-internal-api-key":
        raise ValueError("INTERNAL_API_KEY must not use development default in production")
    return settings