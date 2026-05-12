"""Binance REST API client for fetching historical klines.

Includes a small in-process TTL cache to dampen burst traffic and avoid the
public endpoint's rate limits (~1200 req/min). The cache key includes symbol,
interval and the requested number of bars.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.cryptos import SUPPORTED_SYMBOLS
from app.schemas.kline import KlinePoint

logger = logging.getLogger(__name__)


@dataclass
class _CacheEntry:
    expires_at: float
    payload: list[KlinePoint]


class BinanceService:
    def __init__(self, base_url: str | None = None, ttl_seconds: int | None = None) -> None:
        settings = get_settings()
        self._base_url = base_url or settings.binance_api_base
        self._ttl = ttl_seconds if ttl_seconds is not None else settings.kline_cache_ttl_seconds
        self._cache: dict[tuple[str, str, int], _CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get_klines(
        self,
        symbol: str,
        interval: str = "15m",
        limit: int = 96,
    ) -> list[KlinePoint]:
        upper = symbol.upper()
        if upper not in SUPPORTED_SYMBOLS:
            raise HTTPException(status_code=400, detail=f"unsupported symbol: {symbol}")
        if limit < 1 or limit > 1000:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")

        key = (upper, interval, limit)
        now = time.monotonic()

        cached = self._cache.get(key)
        if cached and cached.expires_at > now:
            return cached.payload

        async with self._lock:
            cached = self._cache.get(key)
            if cached and cached.expires_at > time.monotonic():
                return cached.payload

            url = f"{self._base_url}/api/v3/klines"
            params = {"symbol": upper, "interval": interval, "limit": limit}
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    raw: list[list] = response.json()
            except httpx.HTTPStatusError as exc:
                logger.warning("Binance klines error %s: %s", exc.response.status_code, exc.response.text)
                raise HTTPException(
                    status_code=502,
                    detail=f"binance upstream error: {exc.response.status_code}",
                ) from exc
            except httpx.HTTPError as exc:
                logger.warning("Binance request failed: %s", exc)
                raise HTTPException(status_code=502, detail="binance upstream unreachable") from exc

            # Each kline entry layout:
            # [openTime, open, high, low, close, volume, closeTime, ...]
            points = [
                KlinePoint(open_time=int(row[0]), close=float(row[4]))
                for row in raw
            ]
            self._cache[key] = _CacheEntry(
                expires_at=time.monotonic() + self._ttl,
                payload=points,
            )
            return points


_binance_service: BinanceService | None = None


def get_binance_service() -> BinanceService:
    global _binance_service
    if _binance_service is None:
        _binance_service = BinanceService()
    return _binance_service
