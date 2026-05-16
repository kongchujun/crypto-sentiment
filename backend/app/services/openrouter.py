"""OpenRouter chat completions client."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OpenRouterError(RuntimeError):
    """Raised when OpenRouter returns an error or the response is unusable."""


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must not be empty")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def chat_json(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Call chat/completions and parse the assistant message as JSON."""
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "Crypto Sentiment",
        }
        body: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, headers=headers, json=body)

        if resp.status_code == 401:
            raise OpenRouterError("401 unauthorized (bad OPENROUTER_API_KEY)")
        if resp.status_code == 429:
            raise OpenRouterError("429 rate limited by OpenRouter")
        if resp.status_code >= 400:
            raise OpenRouterError(f"HTTP {resp.status_code}: {resp.text[:300]}")

        payload = resp.json()
        choices = payload.get("choices") or []
        if not choices:
            raise OpenRouterError("empty choices in OpenRouter response")

        content = choices[0].get("message", {}).get("content")
        if not content or not isinstance(content, str):
            raise OpenRouterError("missing assistant content in OpenRouter response")

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            logger.warning("OpenRouter returned non-JSON content: %s", content[:200])
            raise OpenRouterError("assistant response is not valid JSON") from exc
