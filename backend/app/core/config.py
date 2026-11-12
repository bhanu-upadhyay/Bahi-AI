from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "Bahi-AI"
    APP_ENV: str = "development"
    DEBUG: bool = False

    DATABASE_URL: str
    JWT_SECRET_KEY: str = "dev-secret-key-bahi-ai-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    OPENAI_API_KEY: str = ""
    FRONTEND_URL: str = "http://localhost:3000"

    # LLM & Gemini Orchestration Configuration
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-3.5-flash-lite"
    LLM_API_KEY: str = ""
    LLM_TIMEOUT: float = 30.0
    LLM_MAX_TOKENS: int = 2048
    LLM_FALLBACK_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=(_ENV_FILE, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
