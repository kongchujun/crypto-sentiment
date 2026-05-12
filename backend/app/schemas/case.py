from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.cryptos import SUPPORTED_SYMBOLS


class CaseCreate(BaseModel):
    symbol: str = Field(..., description="Binance trading pair, e.g. BTCUSDT")

    @field_validator("symbol")
    @classmethod
    def _validate_symbol(cls, v: str) -> str:
        upper = v.upper()
        if upper not in SUPPORTED_SYMBOLS:
            raise ValueError(f"unsupported symbol: {v}")
        return upper


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    created_at: datetime
