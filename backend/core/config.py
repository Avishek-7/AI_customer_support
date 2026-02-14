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

    # Redis (for rate limiting)
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"

    # Chat response cache
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 1800
    CACHE_PREFIX: str = "chat"

    # Frontend URL (for password reset links)
    FRONTEND_URL: str = "http://localhost:3000"

    # Email / SMTP settings
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    SMTP_FROM: str = "MeetingIntel <no-reply@local.test>"

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra env vars like old celery settings

settings = Settings()

