"""Async client for the twitterapi.io advanced_search endpoint.

Production-side port of ``tests/try_twitterapi_io.py``: same query templates and
normalisation logic, but built on ``httpx.AsyncClient`` so it can be awaited
from the background fetcher without blocking the event loop.

Endpoint reference:
    GET https://api.twitterapi.io/twitter/tweet/advanced_search

If twitterapi.io changes their response schema, update :func:`_normalize`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

API_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"

# Curated queries per short symbol. Kept in sync with tests/try_twitterapi_io.py
# so behaviour matches the exploration scripts.
SYMBOL_QUERIES: dict[str, str] = {
    "BTC": "(#Bitcoin OR #BTC OR Bitcoin) -is:retweet",
    "ETH": "(#Ethereum OR #ETH OR Ethereum) -is:retweet",
    "BNB": "(#BNB OR #BinanceCoin) -is:retweet",
    "SOL": "(#Solana OR #SOL) -is:retweet",
    "XRP": "(#XRP OR #Ripple) -is:retweet",
    "ADA": "(#Cardano OR #ADA) -is:retweet",
    "DOGE": "(#Dogecoin OR #DOGE) -is:retweet",
    "AVAX": "(#Avalanche OR #AVAX) -is:retweet",
    "DOT": "(#Polkadot OR #DOT) -is:retweet",
    "TRX": "(#TRON OR #TRX) -is:retweet",
}


class TwitterApiIoError(RuntimeError):
    """Raised for upstream failures we want the caller to log + skip."""


def build_query(
    short_symbol: str,
    *,
    lang: str | None = "en",
    hours: int = 24,
    min_faves: int = 0,
) -> str:
    base = SYMBOL_QUERIES.get(
        short_symbol.upper(), f"#{short_symbol.upper()} -is:retweet"
    )
    parts = [base]
    if lang and lang.lower() != "none":
        parts.append(f"lang:{lang}")
    if min_faves > 0:
        parts.append(f"min_faves:{min_faves}")
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime(
        "%Y-%m-%d_%H:%M:%S_UTC"
    )
    parts.append(f"since:{since}")
    return " ".join(parts)


def _parse_created_at(value: str) -> datetime | None:
    """twitterapi.io returns either Twitter-classic format or ISO-8601."""
    if not value:
        return None
    try:
        dt = datetime.strptime(value, "%a %b %d %H:%M:%S %z %Y")
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _normalize(tweet: dict[str, Any]) -> dict[str, Any] | None:
    author = tweet.get("author") or {}
    tid = tweet.get("id") or tweet.get("rest_id")
    if not tid:
        return None
    text = (tweet.get("text") or tweet.get("full_text") or "").strip()
    if not text:
        return None
    created_dt = _parse_created_at(
        tweet.get("createdAt") or tweet.get("created_at") or ""
    )
    if created_dt is None:
        return None
    return {
        "id": str(tid),
        "author_handle": "@"
        + (author.get("userName") or author.get("screen_name") or "unknown"),
        "author_name": author.get("name") or None,
        "verified": bool(
            author.get("isBlueVerified") or author.get("verified")
        ),
        "content": text,
        "created_at": created_dt,
        "likes": int(tweet.get("likeCount") or tweet.get("favorite_count") or 0),
        "retweets": int(
            tweet.get("retweetCount") or tweet.get("retweet_count") or 0
        ),
        "replies": int(tweet.get("replyCount") or tweet.get("reply_count") or 0),
        "quotes": int(tweet.get("quoteCount") or tweet.get("quote_count") or 0),
        "url": tweet.get("url") or None,
    }


class TwitterApiIoClient:
    """Thin async wrapper around twitterapi.io advanced_search.

    The client opens a fresh ``httpx.AsyncClient`` per fetch_top_posts call so
    it is safe to instantiate once and reuse across many scheduled runs.
    """

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 20.0,
        max_pages: int = 5,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must not be empty")
        self._api_key = api_key
        self._timeout = timeout
        self._max_pages = max_pages

    async def fetch_top_posts(
        self,
        short_symbol: str,
        *,
        limit: int = 20,
        hours: int = 24,
        lang: str | None = None,
        min_faves: int = 0,
    ) -> list[dict[str, Any]]:
        """Return up to ``limit`` normalised tweets sorted by likes desc."""
        query = build_query(
            short_symbol, lang=lang, hours=hours, min_faves=min_faves
        )
        headers = {"X-API-Key": self._api_key, "Accept": "application/json"}

        raw_tweets: list[dict[str, Any]] = []
        cursor: str | None = None
        pages = 0

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            while len(raw_tweets) < limit and pages < self._max_pages:
                params: dict[str, str] = {"query": query, "queryType": "Top"}
                if cursor:
                    params["cursor"] = cursor
                resp = await client.get(API_URL, headers=headers, params=params)
                if resp.status_code == 401:
                    raise TwitterApiIoError(
                        "401 unauthorized (bad TWITTERAPI_IO_KEY)"
                    )
                if resp.status_code == 429:
                    raise TwitterApiIoError("429 rate limited by twitterapi.io")
                if resp.status_code >= 400:
                    raise TwitterApiIoError(
                        f"HTTP {resp.status_code}: {resp.text[:200]}"
                    )
                payload = resp.json()
                batch = payload.get("tweets") or payload.get("data") or []
                raw_tweets.extend(batch)
                cursor = payload.get("next_cursor") or payload.get("cursor")
                has_next = payload.get("has_next_page", bool(cursor))
                if not has_next or not batch:
                    break
                pages += 1

        normalised: list[dict[str, Any]] = []
        for raw in raw_tweets:
            row = _normalize(raw)
            if row is not None:
                normalised.append(row)
        normalised.sort(key=lambda r: r["likes"], reverse=True)
        return normalised[:limit]
