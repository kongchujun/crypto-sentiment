from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path

from app.core.config import Settings, get_settings
from app.schemas.prediction import (
    ModelOption,
    ModelsResponse,
    PredictRequest,
    PricePrediction,
)
from app.services.prediction import PredictionService

router = APIRouter(tags=["prediction"])


def _model_label(model_id: str) -> str:
    return model_id.split("/")[-1].replace("-", " ").title()


@router.get("/prediction/models", response_model=ModelsResponse)
async def list_prediction_models(
    settings: Settings = Depends(get_settings),
) -> ModelsResponse:
    models = [
        ModelOption(id=m, label=_model_label(m))
        for m in settings.openrouter_models_list
    ]
    return ModelsResponse(
        models=models,
        default_model=settings.openrouter_default_model,
    )


@router.post("/cryptos/{symbol}/predict", response_model=PricePrediction)
async def predict_price(
    payload: PredictRequest,
    symbol: str = Path(..., description="Trading pair symbol, e.g. BTCUSDT"),
    settings: Settings = Depends(get_settings),
) -> PricePrediction:
    if not settings.openrouter_api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENROUTER_API_KEY is not set. Add it to backend/.env to enable predictions.",
        )
    service = PredictionService(settings)
    return await service.predict(
        symbol=symbol,
        posts=payload.posts,
        klines=payload.klines,
        model=payload.model,
    )
