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

    # X (Twitter) ingestion config. When TWITTERAPI_IO_KEY is empty the
    # background fetcher is silently disabled, so the app still boots without
    # any X credentials.
    twitterapi_io_key: str = Field(default="", alias="TWITTERAPI_IO_KEY")
    x_fetch_symbols: str = Field(
        default="BTCUSDT,ETHUSDT,DOGEUSDT", alias="X_FETCH_SYMBOLS"
    )
    x_fetch_interval_seconds: int = Field(
        default=3600, alias="X_FETCH_INTERVAL_SECONDS"
    )
    x_fetch_limit_per_symbol: int = Field(
        default=20, alias="X_FETCH_LIMIT_PER_SYMBOL"
    )
    x_fetch_lookback_hours: int = Field(default=24, alias="X_FETCH_LOOKBACK_HOURS")
    x_fetch_lang: str = Field(default="en", alias="X_FETCH_LANG")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def x_fetch_symbols_list(self) -> list[str]:
        return [s.strip().upper() for s in self.x_fetch_symbols.split(",") if s.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
