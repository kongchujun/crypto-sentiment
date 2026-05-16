from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="postgresql+asyncpg://crypto:crypto@localhost:5432/crypto_sentiment",
        alias="DATABASE_URL",
    )
    binance_api_base: str = Field(default="https://api.binance.com", alias="BINANCE_API_BASE")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173", alias="CORS_ORIGINS"
    )
    kline_cache_ttl_seconds: int = Field(default=30, alias="KLINE_CACHE_TTL_SECONDS")

    # twitterapi.io key for live X posts. When empty, /cryptos/{symbol}/posts
    # falls back to mock fixture data.
    twitterapi_io_key: str = Field(default="", alias="TWITTERAPI_IO_KEY")

    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL"
    )
    openrouter_default_model: str = Field(
        default="openai/gpt-4o-mini", alias="OPENROUTER_DEFAULT_MODEL"
    )
    openrouter_models: str = Field(
        default=(
            "openai/gpt-4o-mini,openai/gpt-4o,"
            "anthropic/claude-3.5-sonnet,google/gemini-2.0-flash-001"
        ),
        alias="OPENROUTER_MODELS",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def openrouter_models_list(self) -> list[str]:
        return [m.strip() for m in self.openrouter_models.split(",") if m.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
