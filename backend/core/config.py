from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "AI Customer Support Backend"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 1 day

    # Database
    DATABASE_URL: str

    # AI Engine
    AI_ENGINE_URL: str

    # Celery
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings()

