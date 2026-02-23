from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    GOOGLE_API_KEY: Optional[str] = None
    BACKEND_URL: str = "http://localhost:8000"
    INTERNAL_API_KEY: str = "dev-internal-api-key"
    ENABLE_MMR_RERANK: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra env vars


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()