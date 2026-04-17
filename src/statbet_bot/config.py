from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    telegram_token: str = Field(..., min_length=10)
    database_url: str = Field("postgresql://user:password@localhost/statbet")
    redis_url: str = Field("redis://localhost:6379")
    api_football_key: Optional[str] = Field(None)
    odds_api_key: Optional[str] = Field(None)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    @field_validator("telegram_token")
    @classmethod
    def token_must_not_be_placeholder(cls, v: str) -> str:
        if v.lower() in ("your_token_here", "changeme", ""):
            raise ValueError("TELEGRAM_TOKEN не настроен — укажите реальный токен в .env")
        return v

    @field_validator("database_url")
    @classmethod
    def database_url_must_be_valid(cls, v: str) -> str:
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError("DATABASE_URL должен начинаться с postgresql:// или postgres://")
        return v

    @classmethod
    def load(cls) -> "Config":
        """Load and validate configuration from environment / .env file."""
        return cls()