"""X (Twitter) post providers for the /cryptos/{symbol}/posts API.

Posts are fetched on demand and returned to the client only; nothing is
persisted to Postgres.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path

from fastapi import HTTPException

from app.core.config import Settings, get_settings
from app.core.cryptos import get_crypto
from app.schemas.post import XPost
from app.services.twitterapi_io import TwitterApiIoClient, TwitterApiIoError

_MOCK_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_posts.json"


class XPostsProvider(ABC):
    @abstractmethod
    async def top_posts(self, symbol: str, limit: int = 5) -> list[XPost]:
        """Return the top `limit` posts for `symbol` ordered by hotness."""


class TwitterApiIoPostsProvider(XPostsProvider):
    """Fetch posts live from twitterapi.io when the UI requests them."""

    def __init__(self, settings: Settings) -> None:
        if not settings.twitterapi_io_key:
            raise ValueError("TWITTERAPI_IO_KEY is required")
        self._client = TwitterApiIoClient(api_key=settings.twitterapi_io_key)

    async def top_posts(self, symbol: str, limit: int = 5) -> list[XPost]:
        meta = get_crypto(symbol)
        short = meta.base_asset if meta is not None else symbol.upper().removesuffix("USDT")
        try:
            rows = await self._client.fetch_top_posts(short, limit=limit)
        except TwitterApiIoError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        posts: list[XPost] = []
        for row in rows:
            created_at = row["created_at"]
            posts.append(
                XPost(
                    id=row["id"],
                    author=row["author_handle"],
                    content=row["content"],
                    created_at=int(created_at.timestamp() * 1000),
                    likes=row["likes"],
                    retweets=row["retweets"],
                    url=row["url"],
                )
            )
        return posts


class MockXPostsProvider(XPostsProvider):
    def __init__(self, fixture_path: Path | None = None) -> None:
        self._fixture_path = fixture_path or _MOCK_PATH
        self._fixtures: dict[str, list[dict]] | None = None

    def _load(self) -> dict[str, list[dict]]:
        if self._fixtures is None:
            with self._fixture_path.open("r", encoding="utf-8") as fh:
                self._fixtures = json.load(fh)
        return self._fixtures

    async def top_posts(self, symbol: str, limit: int = 5) -> list[XPost]:
        fixtures = self._load()
        raw = fixtures.get(symbol.upper(), [])
        now_ms = int(time.time() * 1000)
        posts: list[XPost] = []
        for row in raw:
            created_at = now_ms - int(row["minutes_ago"]) * 60_000
            posts.append(
                XPost(
                    id=row["id"],
                    author=row["author"],
                    content=row["content"],
                    created_at=created_at,
                    likes=int(row.get("likes", 0)),
                    retweets=int(row.get("retweets", 0)),
                    url=row.get("url"),
                )
            )
        posts.sort(key=lambda p: (p.likes + p.retweets * 2), reverse=True)
        return posts[:limit]


_provider: XPostsProvider | None = None


def get_x_posts_provider() -> XPostsProvider:
    global _provider
    if _provider is None:
        settings = get_settings()
        if settings.twitterapi_io_key:
            _provider = TwitterApiIoPostsProvider(settings)
        else:
            _provider = MockXPostsProvider()
    return _provider
