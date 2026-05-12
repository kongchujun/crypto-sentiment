"""Fetch top-liked X posts about a crypto via twitterapi.io.

Why this exists
---------------
twitterapi.io is a third-party proxy on top of X data that supports the FULL
X search syntax (including ``min_faves:1000`` and ``since:``/``until:``),
so we can filter and rank server-side and don't need a Pro X subscription.

Auth
----
1. Sign up at https://twitterapi.io
2. Copy your API key from the dashboard
3. Put it in ``backend/.env`` :   TWITTERAPI_IO_KEY=...

Endpoint used
-------------
GET https://api.twitterapi.io/twitter/tweet/advanced_search

If twitterapi.io changes their schema in the future, check their docs at
https://docs.twitterapi.io and adjust ``API_URL`` / parameter names below.

Usage
-----
    cd backend
    source .venv/bin/activate

    python tests/try_twitterapi_io.py BTC
    python tests/try_twitterapi_io.py ETH --limit 10
    python tests/try_twitterapi_io.py DOGE --hours 6
    python tests/try_twitterapi_io.py BTC --min-faves 500
    python tests/try_twitterapi_io.py XRP --lang none
    python tests/try_twitterapi_io.py BTC --json | jq .
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"
load_dotenv(_ENV_FILE, override=False)

API_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"

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


def get_key() -> str:
    key = os.environ.get("TWITTERAPI_IO_KEY") or os.environ.get("TWITTER_API_IO_KEY")
    if not key:
        print(
            "ERROR: TWITTERAPI_IO_KEY is not set.\n"
            f"  Tried .env file at: {_ENV_FILE}\n"
            "    (add a line:  TWITTERAPI_IO_KEY=your_key_here)",
            file=sys.stderr,
        )
        sys.exit(2)
    return key


def build_query(symbol: str, lang: str | None, hours: int, min_faves: int) -> str:
    base = SYMBOL_QUERIES.get(symbol.upper(), f"#{symbol.upper()} -is:retweet")
    parts = [base]
    if lang:
        parts.append(f"lang:{lang}")
    if min_faves > 0:
        parts.append(f"min_faves:{min_faves}")
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime(
        "%Y-%m-%d_%H:%M:%S_UTC"
    )
    parts.append(f"since:{since}")
    return " ".join(parts)


def fetch(query: str, limit: int) -> list[dict[str, Any]]:
    key = get_key()
    headers = {"X-API-Key": key, "Accept": "application/json"}
    params = {"query": query, "queryType": "Top"}

    tweets: list[dict[str, Any]] = []
    cursor: str | None = None
    pages = 0

    with httpx.Client(timeout=20.0) as client:
        while len(tweets) < limit and pages < 5:
            page_params = dict(params)
            if cursor:
                page_params["cursor"] = cursor
            resp = client.get(API_URL, headers=headers, params=page_params)
            if resp.status_code == 401:
                print("ERROR: 401 Unauthorized. Bad TWITTERAPI_IO_KEY.", file=sys.stderr)
                sys.exit(4)
            if resp.status_code == 429:
                print("ERROR: 429 Rate limited by twitterapi.io.", file=sys.stderr)
                sys.exit(3)
            if resp.status_code >= 400:
                print(f"ERROR: HTTP {resp.status_code}\n{resp.text}", file=sys.stderr)
                sys.exit(6)
            payload = resp.json()
            # twitterapi.io returns:  { tweets: [...], has_next_page, next_cursor }
            batch = payload.get("tweets") or payload.get("data") or []
            tweets.extend(batch)
            cursor = payload.get("next_cursor") or payload.get("cursor")
            has_next = payload.get("has_next_page", bool(cursor))
            if not has_next or not batch:
                break
            pages += 1

    return tweets[:limit]


def normalize(t: dict[str, Any]) -> dict[str, Any]:
    """Shape twitterapi.io's tweet into a common dict for printing."""
    author = t.get("author") or {}
    return {
        "id": t.get("id") or t.get("rest_id") or "",
        "author_handle": "@" + (author.get("userName") or author.get("screen_name") or "unknown"),
        "author_name": author.get("name", ""),
        "verified": bool(author.get("isBlueVerified") or author.get("verified")),
        "created_at": t.get("createdAt") or t.get("created_at") or "",
        "text": (t.get("text") or t.get("full_text") or "").strip(),
        "likes": int(t.get("likeCount") or t.get("favorite_count") or 0),
        "retweets": int(t.get("retweetCount") or t.get("retweet_count") or 0),
        "replies": int(t.get("replyCount") or t.get("reply_count") or 0),
        "quotes": int(t.get("quoteCount") or t.get("quote_count") or 0),
        "url": t.get("url") or "",
    }


def render(tweets: list[dict[str, Any]], query: str, sort_mode: str, limit: int) -> None:
    rows = [normalize(t) for t in tweets]
    rows.sort(
        key=lambda r: r["likes"] if sort_mode == "likes" else (r["likes"] + 2 * r["retweets"]),
        reverse=True,
    )
    rows = rows[:limit]

    print(f"Provider : twitterapi.io")
    print(f"Query    : {query}")
    print(f"Scanned  : {len(tweets)}")
    print(f"Sorted by: {sort_mode}")
    print(f"Showing  : top {len(rows)}")
    print("-" * 80)
    if not rows:
        print("No tweets returned.")
        return
    for i, r in enumerate(rows, 1):
        verified = " [verified]" if r["verified"] else ""
        text = r["text"].replace("\n", " ")
        print(f"\n[{i}] {r['author_handle']}{verified}  ({r['author_name']})  {r['created_at']}")
        print(
            f"    likes={r['likes']}  retweets={r['retweets']}  "
            f"replies={r['replies']}  quotes={r['quotes']}"
        )
        print(f"    {text}")
        if r["url"]:
            print(f"    {r['url']}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch top-liked X posts about a crypto via twitterapi.io.",
    )
    parser.add_argument("symbol", help="Crypto symbol, e.g. BTC, ETH, SOL")
    parser.add_argument("--limit", type=int, default=5, help="Top tweets to show (default 5)")
    parser.add_argument("--hours", type=int, default=24, help="Lookback window in hours (default 24)")
    parser.add_argument(
        "--min-faves",
        type=int,
        default=0,
        help="Server-side filter: only tweets with >= this many likes (default 0 = no filter)",
    )
    parser.add_argument(
        "--sort",
        choices=["likes", "engagement"],
        default="likes",
        help="Local re-sort applied to the returned pool",
    )
    parser.add_argument(
        "--lang", default="en", help="Language filter (e.g. 'en', 'zh', 'none' to disable)"
    )
    parser.add_argument("--json", action="store_true", help="Raw normalized JSON")
    args = parser.parse_args()

    lang = None if args.lang.lower() == "none" else args.lang
    query = build_query(args.symbol, lang, args.hours, args.min_faves)
    tweets = fetch(query, limit=max(args.limit, 20))

    if args.json:
        rows = [normalize(t) for t in tweets]
        rows.sort(
            key=lambda r: r["likes"]
            if args.sort == "likes"
            else (r["likes"] + 2 * r["retweets"]),
            reverse=True,
        )
        out = {
            "provider": "twitterapi.io",
            "query": query,
            "sort": args.sort,
            "tweets": rows[: args.limit],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        render(tweets, query, args.sort, args.limit)


if __name__ == "__main__":
    main()
