from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.kline import KlinePoint
from app.schemas.post import XPost

Direction = Literal["bullish", "bearish", "neutral"]


class ForecastPoint(BaseModel):
    open_time: int = Field(..., description="Forecast time, epoch milliseconds (UTC)")
    price: float = Field(..., description="Predicted price at open_time")


class PricePrediction(BaseModel):
    direction: Direction
    confidence: float = Field(..., ge=0.0, le=1.0)
    horizon_hours: int = Field(..., ge=1, le=24)
    summary: str
    forecast_points: list[ForecastPoint]
    model: str


class PredictRequest(BaseModel):
    model: str | None = None
    posts: list[XPost] = Field(..., min_length=1)
    klines: list[KlinePoint] = Field(..., min_length=1)


class ModelOption(BaseModel):
    id: str
    label: str


class ModelsResponse(BaseModel):
    models: list[ModelOption]
    default_model: str


class LlmForecastPoint(BaseModel):
    hours_ahead: int = Field(..., ge=1, le=24)
    price: float = Field(..., gt=0)


class LlmPredictionResponse(BaseModel):
    direction: Direction
    confidence: float = Field(..., ge=0.0, le=1.0)
    horizon_hours: int = Field(..., ge=1, le=24)
    summary: str
    forecast_points: list[LlmForecastPoint]
