"""Background X posts ingester.

For each configured Binance pair symbol (e.g. ``BTCUSDT``) the fetcher:

1. Maps it to the X short symbol (``BTCUSDT`` -> ``BTC``).
2. Calls twitterapi.io for the top liked tweets in the last
   ``X_FETCH_LOOKBACK_HOURS``.
3. Upserts rows into ``x_posts`` keyed on the tweet id, refreshing engagement
   counters and ``updated_at`` on conflict so the same tweet never inserts
   twice.

The fetcher runs once on app startup and then every
``X_FETCH_INTERVAL_SECONDS``. If ``TWITTERAPI_IO_KEY`` is empty the scheduler
is silently disabled so the app boots cleanly without credentials.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import Settings
from app.core.cryptos import get_crypto
from app.db.session import AsyncSessionLocal
from app.models.x_post import XPostRecord
from app.services.twitterapi_io import (
    TwitterApiIoClient,
    TwitterApiIoError,
)

logger = logging.getLogger(__name__)


def _short_symbol(symbol: str) -> str | None:
    """Map a Binance trading pair to its X short symbol.

    ``BTCUSDT`` -> ``BTC``. Falls back to stripping a ``USDT`` suffix so newly
    added pairs work without a code change. Returns None if we can't derive a
    usable code (which lets the caller skip that symbol).
    """
    meta = get_crypto(symbol)
    if meta is not None:
        return meta.base_asset
    upper = symbol.upper()
    if upper.endswith("USDT") and len(upper) > 4:
        return upper[:-4]
    return upper or None


class XPostsFetcher:
    """Fetch + persist a batch of X posts for the configured symbols."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = TwitterApiIoClient(api_key=settings.twitterapi_io_key)

    async def fetch_once(self) -> dict[str, int]:
        """Fetch every configured symbol once. Returns ``{symbol: upserted}``."""
        results: dict[str, int] = {}
        for symbol in self._settings.x_fetch_symbols_list:
            short = _short_symbol(symbol)
            if short is None:
                logger.warning("x-fetch: cannot derive short code for %s", symbol)
                results[symbol] = 0
                continue
            try:
                rows = await self._client.fetch_top_posts(
                    short,
                    limit=self._settings.x_fetch_limit_per_symbol,
                    hours=self._settings.x_fetch_lookback_hours,
                    lang=self._settings.x_fetch_lang,
                )
            except TwitterApiIoError as exc:
                logger.error("x-fetch: %s upstream failure: %s", symbol, exc)
                results[symbol] = 0
                continue
            except Exception:
                # Network / parsing / anything unexpected: log and skip this
                # symbol, but keep the loop alive for the others.
                logger.exception("x-fetch: %s unexpected error", symbol)
                results[symbol] = 0
                continue

            count = await self._upsert(symbol, rows)
            results[symbol] = count
            logger.info(
                "x-fetch: %s fetched=%d upserted=%d", symbol, len(rows), count
            )
        return results

    async def _upsert(self, symbol: str, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        payload = [
            {
                "id": r["id"],
                "symbol": symbol,
                "author_handle": r["author_handle"],
                "author_name": r["author_name"],
                "verified": r["verified"],
                "content": r["content"],
                "created_at": r["created_at"],
                "likes": r["likes"],
                "retweets": r["retweets"],
                "replies": r["replies"],
                "quotes": r["quotes"],
                "url": r["url"],
            }
            for r in rows
        ]
        # Postgres-specific INSERT ... ON CONFLICT (id) DO UPDATE.
        # Engagement counters grow over time so we refresh them on every
        # re-fetch. content / url can be tweaked by the author so we refresh
        # them too. fetched_at intentionally stays the original "first seen"
        # timestamp.
        stmt = pg_insert(XPostRecord).values(payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=[XPostRecord.id],
            set_={
                "likes": stmt.excluded.likes,
                "retweets": stmt.excluded.retweets,
                "replies": stmt.excluded.replies,
                "quotes": stmt.excluded.quotes,
                "content": stmt.excluded.content,
                "url": stmt.excluded.url,
                "updated_at": func.now(),
            },
        )
        async with AsyncSessionLocal() as session:
            await session.execute(stmt)
            await session.commit()
        return len(payload)


async def _run_loop(fetcher: XPostsFetcher, interval_seconds: int) -> None:
    """Run forever: fetch, then sleep, then fetch, ..."""
    while True:
        try:
            await fetcher.fetch_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            # Defensive: fetch_once already swallows per-symbol failures, but
            # we belt-and-brace here so a bug never tears down the loop.
            logger.exception("x-fetch: fatal error in fetch_once")
        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            raise


def start_background_fetcher(settings: Settings) -> asyncio.Task | None:
    """Spawn the periodic fetcher task or return ``None`` if disabled."""
    if not settings.twitterapi_io_key:
        logger.warning(
            "x-fetch: TWITTERAPI_IO_KEY is empty; periodic X-posts fetch is "
            "disabled. Add it to backend/.env to enable."
        )
        return None
    if not settings.x_fetch_symbols_list:
        logger.warning("x-fetch: X_FETCH_SYMBOLS is empty; nothing to fetch")
        return None

    fetcher = XPostsFetcher(settings)
    interval = max(60, int(settings.x_fetch_interval_seconds))
    task = asyncio.create_task(
        _run_loop(fetcher, interval), name="x-posts-fetcher"
    )
    logger.info(
        "x-fetch: scheduled every %ds for symbols=%s",
        interval,
        ",".join(settings.x_fetch_symbols_list),
    )
    return task
