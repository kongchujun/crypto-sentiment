from __future__ import annotations

from pydantic import BaseModel, Field


class KlinePoint(BaseModel):
    open_time: int = Field(..., description="Open time of the candle, epoch milliseconds (UTC)")
    close: float = Field(..., description="Close price")


class CryptoMetaRead(BaseModel):
    symbol: str
    name: str
    base_asset: str
