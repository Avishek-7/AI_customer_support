from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "AI Customer Support Backend"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 1 day

    # Database
    DATABASE_URL: str

    # AI Engine
    AI_ENGINE_URL: str = "http://localhost:8001"

    class Config:
        env_file = ".env"

settings = Settings()

