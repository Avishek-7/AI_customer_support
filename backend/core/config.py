from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "AI Customer Support Backend"

    JWT_SECRET_KEY: str = "test-secret-key-for-testing-only"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 1 day

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"

    # AI Engine
    AI_ENGINE_URL: str = "http://localhost:9000"

    # Redis (for rate limiting)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Chat response cache
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 1800
    CACHE_PREFIX: str = "chat"

    # Frontend URL (for password reset links)
    FRONTEND_URL: str = "http://localhost:3000"

    # Email / SMTP settings
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_TIMEOUT: int = 10
    SMTP_USE_TLS: bool = False
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    SMTP_FROM: str = "AI Customer Support Backend <no-reply@local.test>"

    # Internal service authentication (AI engine -> backend callbacks)
    INTERNAL_API_KEY: str = "test-internal-api-key-for-testing-only"

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

