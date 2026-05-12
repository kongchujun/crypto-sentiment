from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query

from app.core.cryptos import SUPPORTED_CRYPTOS
from app.schemas.kline import CryptoMetaRead, KlinePoint
from app.schemas.post import XPost
from app.services.binance import BinanceService, get_binance_service
from app.services.x_posts import XPostsProvider, get_x_posts_provider

router = APIRouter(prefix="/cryptos", tags=["cryptos"])


@router.get("", response_model=list[CryptoMetaRead])
async def list_cryptos() -> list[CryptoMetaRead]:
    return [
        CryptoMetaRead(symbol=c.symbol, name=c.name, base_asset=c.base_asset)
        for c in SUPPORTED_CRYPTOS
    ]


@router.get("/{symbol}/klines", response_model=list[KlinePoint])
async def get_klines(
    symbol: str = Path(..., description="Trading pair symbol, e.g. BTCUSDT"),
    interval: str = Query("15m", description="Binance kline interval"),
    hours: int = Query(24, ge=1, le=168, description="History window in hours"),
    binance: BinanceService = Depends(get_binance_service),
) -> list[KlinePoint]:
    # Interval -> bar size in minutes; we only expose intervals our UI uses.
    interval_minutes = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "1h": 60,
        "4h": 240,
    }.get(interval)
    if interval_minutes is None:
        # Defer error reporting to Binance for any other interval the caller passes.
        limit = 96
    else:
        limit = max(1, min(1000, (hours * 60) // interval_minutes))
    return await binance.get_klines(symbol=symbol, interval=interval, limit=limit)


@router.get("/{symbol}/posts", response_model=list[XPost])
async def get_posts(
    symbol: str = Path(..., description="Trading pair symbol, e.g. BTCUSDT"),
    limit: int = Query(5, ge=1, le=20),
    provider: XPostsProvider = Depends(get_x_posts_provider),
) -> list[XPost]:
    return await provider.top_posts(symbol=symbol, limit=limit)
