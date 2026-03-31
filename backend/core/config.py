from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "AI Customer Support Backend"

    # Security-sensitive values are required from environment/.env.
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 1 day

    # Database
    DATABASE_URL: str

    # AI Engine
    AI_ENGINE_URL: str

    # Redis (for rate limiting)
    REDIS_URL: str
    RATE_LIMIT_FAIL_CLOSED_ON_REDIS_UNAVAILABLE: bool = True

    # Chat response cache
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 1800
    CACHE_PREFIX: str = "chat"

    # Frontend URL (for password reset links)
    FRONTEND_URL: str

    # Email / SMTP settings
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_TIMEOUT: int = 10
    SMTP_USE_TLS: bool = False
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    SMTP_FROM: str = "AI Customer Support Backend <no-reply@local.test>"

    # Internal service authentication (AI engine -> backend callbacks)
    INTERNAL_API_KEY: str

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra env vars like old celery settings


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the settings singleton instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


# For backward compatibility with existing imports
settings = get_settings()

