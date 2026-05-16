"""Build prompts and run price predictions via OpenRouter."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from pydantic import ValidationError

from app.core.config import Settings
from app.core.cryptos import get_crypto
from app.schemas.kline import KlinePoint
from app.schemas.post import XPost
from app.schemas.prediction import (
    ForecastPoint,
    LlmPredictionResponse,
    PricePrediction,
)
from app.services.openrouter import OpenRouterClient, OpenRouterError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a crypto market sentiment analyst. Based ONLY on the X (Twitter) posts and recent price statistics provided, produce a short-term price direction forecast.

Output rules:
- Respond with a single valid JSON object only. No markdown, no code fences, no extra text.
- This is NOT financial advice; information may be incomplete or stale.
- forecast_points must contain exactly 4 objects with hours_ahead 1, 2, 3, and 4.
- Prices must be positive numbers and form a plausible path relative to last_close.
- For direction "neutral", keep price moves modest (roughly within ~1% of last_close unless posts strongly disagree).
- confidence is between 0.0 and 1.0.
- summary: 2-3 sentences in English explaining the reasoning from post sentiment.

Required JSON schema:
{
  "direction": "bullish" | "bearish" | "neutral",
  "confidence": <number 0-1>,
  "horizon_hours": 4,
  "summary": "<string>",
  "forecast_points": [
    { "hours_ahead": 1, "price": <number> },
    { "hours_ahead": 2, "price": <number> },
    { "hours_ahead": 3, "price": <number> },
    { "hours_ahead": 4, "price": <number> }
  ]
}"""

POST_CONTENT_MAX = 280


def _kline_stats(klines: list[KlinePoint]) -> dict[str, float]:
    closes = [k.close for k in klines]
    first = closes[0]
    last = closes[-1]
    change_pct = ((last - first) / first * 100) if first else 0.0
    return {
        "last_close": last,
        "change_pct_24h": change_pct,
        "high_24h": max(closes),
        "low_24h": min(closes),
    }


def _format_post(post: XPost, index: int) -> str:
    created = datetime.fromtimestamp(post.created_at / 1000, tz=timezone.utc).isoformat()
    content = post.content
    if len(content) > POST_CONTENT_MAX:
        content = content[:POST_CONTENT_MAX] + "…"
    return (
        f"{index}. {post.author} | likes={post.likes} retweets={post.retweets} | "
        f"{created}\n   {content}"
    )


def build_user_prompt(
    symbol: str,
    name: str,
    stats: dict[str, float],
    posts: list[XPost],
) -> str:
    sorted_posts = sorted(posts, key=lambda p: p.likes, reverse=True)
    post_blocks = "\n\n".join(
        _format_post(p, i + 1) for i, p in enumerate(sorted_posts)
    )
    return f"""Asset: {name} ({symbol})
Price stats (24h window):
- last_close: {stats['last_close']:.8g}
- change_pct_24h: {stats['change_pct_24h']:.2f}%
- high_24h: {stats['high_24h']:.8g}
- low_24h: {stats['low_24h']:.8g}

X posts (sorted by likes):
{post_blocks}

Forecast the next 4 hours (hours_ahead 1-4) from last_close based on post sentiment and price context."""


def _to_chart_points(
    llm: LlmPredictionResponse,
    last_open_time: int,
) -> list[ForecastPoint]:
    by_hour = {p.hours_ahead: p.price for p in llm.forecast_points}
    expected = [1, 2, 3, 4]
    if set(by_hour.keys()) != set(expected):
        raise ValueError(
            f"forecast_points must have hours_ahead {expected}, got {sorted(by_hour.keys())}"
        )
    return [
        ForecastPoint(
            open_time=last_open_time + h * 3_600_000,
            price=by_hour[h],
        )
        for h in expected
    ]


class PredictionService:
    def __init__(self, settings: Settings) -> None:
        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
        self._settings = settings
        self._client = OpenRouterClient(
            settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )

    async def predict(
        self,
        symbol: str,
        posts: list[XPost],
        klines: list[KlinePoint],
        model: str | None = None,
    ) -> PricePrediction:
        meta = get_crypto(symbol)
        name = meta.name if meta else symbol
        stats = _kline_stats(klines)
        last_open_time = klines[-1].open_time
        user_prompt = build_user_prompt(symbol, name, stats, posts)
        chosen_model = model or self._settings.openrouter_default_model

        last_error: Exception | None = None
        for attempt, temperature in enumerate((0.2, 0.0)):
            try:
                raw = await self._client.chat_json(
                    model=chosen_model,
                    system=SYSTEM_PROMPT,
                    user=user_prompt,
                    temperature=temperature,
                )
                llm = LlmPredictionResponse.model_validate(raw)
                chart_points = _to_chart_points(llm, last_open_time)
                return PricePrediction(
                    direction=llm.direction,
                    confidence=llm.confidence,
                    horizon_hours=llm.horizon_hours,
                    summary=llm.summary,
                    forecast_points=chart_points,
                    model=chosen_model,
                )
            except (OpenRouterError, ValueError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "prediction attempt %d failed for %s: %s",
                    attempt + 1,
                    symbol,
                    exc,
                )

        detail = str(last_error) if last_error else "prediction failed"
        raise HTTPException(status_code=502, detail=detail) from last_error
