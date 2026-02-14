from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    GOOGLE_API_KEY: str
    BACKEND_URL: str = "http://localhost:8000"
    ENABLE_MMR_RERANK: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra env vars
    
settings = Settings()