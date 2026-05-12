"""X (Twitter) post providers.

Stage 1 ships only a mock provider that reads fixture data from
`app/data/mock_posts.json`. The abstract base class fixes the contract for the
future real provider (X API v2, Apify, etc.). Each fixture entry stores a
`minutes_ago` offset rather than an absolute timestamp so post times always
land within the last 24h relative to "now".
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path

from fastapi import HTTPException

from app.core.cryptos import SUPPORTED_SYMBOLS
from app.schemas.post import XPost

_MOCK_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_posts.json"


class XPostsProvider(ABC):
    @abstractmethod
    async def top_posts(self, symbol: str, limit: int = 5) -> list[XPost]:
        """Return the top `limit` posts for `symbol` ordered by hotness."""


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
        upper = symbol.upper()
        if upper not in SUPPORTED_SYMBOLS:
            raise HTTPException(status_code=400, detail=f"unsupported symbol: {symbol}")

        fixtures = self._load()
        raw = fixtures.get(upper, [])
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
        _provider = MockXPostsProvider()
    return _provider
