"""Fetch top-liked X posts about a crypto via the Apify Tweet Scraper actor.

Why this exists
---------------
Apify is a scraping-as-a-service platform. Their public actor
``apidojo/tweet-scraper`` scrapes X for a given search query and returns
a JSON dataset. The free tier gives ~$5/month of credit, and the actor
itself runs around $0.40 per 1k tweets.

Auth
----
1. Sign up at https://apify.com
2. Find your API token at https://console.apify.com/account/integrations
3. Put it in ``backend/.env`` :   APIFY_TOKEN=...

Actor & endpoint
----------------
Actor used: ``apidojo/tweet-scraper`` (most popular X scraper as of 2026)
Run-sync endpoint:
    POST https://api.apify.com/v2/acts/apidojo~tweet-scraper/run-sync-get-dataset-items

If the actor's input schema or name changes, see
https://apify.com/apidojo/tweet-scraper for the current spec.

Usage
-----
    cd backend
    source .venv/bin/activate

    python tests/try_apify.py BTC
    python tests/try_apify.py ETH --limit 10
    python tests/try_apify.py DOGE --hours 6
    python tests/try_apify.py BTC --min-faves 500
    python tests/try_apify.py XRP --lang none
    python tests/try_apify.py BTC --json | jq .
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

# Actor slug uses '~' to separate user and actor in the API URL.
ACTOR = "apidojo~tweet-scraper"
RUN_SYNC_URL = f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items"

# Same per-symbol queries we use elsewhere.
SYMBOL_QUERIES: dict[str, list[str]] = {
    "BTC": ["#Bitcoin", "#BTC", "Bitcoin"],
    "ETH": ["#Ethereum", "#ETH", "Ethereum"],
    "BNB": ["#BNB", "#BinanceCoin"],
    "SOL": ["#Solana", "#SOL"],
    "XRP": ["#XRP", "#Ripple"],
    "ADA": ["#Cardano", "#ADA"],
    "DOGE": ["#Dogecoin", "#DOGE"],
    "AVAX": ["#Avalanche", "#AVAX"],
    "DOT": ["#Polkadot", "#DOT"],
    "TRX": ["#TRON", "#TRX"],
}


def get_token() -> str:
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        print(
            "ERROR: APIFY_TOKEN is not set.\n"
            f"  Tried .env file at: {_ENV_FILE}\n"
            "    (add a line:  APIFY_TOKEN=your_token_here)",
            file=sys.stderr,
        )
        sys.exit(2)
    return token


def build_terms(symbol: str) -> list[str]:
    return SYMBOL_QUERIES.get(symbol.upper(), [f"#{symbol.upper()}"])


def fetch(symbol: str, hours: int, lang: str | None, min_faves: int, max_items: int) -> list[dict[str, Any]]:
    token = get_token()
    start_iso = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )

    # See https://apify.com/apidojo/tweet-scraper for the full input schema.
    input_payload: dict[str, Any] = {
        "searchTerms": build_terms(symbol),
        "sort": "Top",
        "maxItems": max_items,
        "start": start_iso,
        "tweetLanguage": lang if lang else None,
        "minimumFavorites": min_faves if min_faves > 0 else None,
        "includeSearchTerms": False,
    }
    # Remove None fields so we don't override actor defaults.
    input_payload = {k: v for k, v in input_payload.items() if v is not None}

    params = {"token": token, "timeout": 180, "memory": 512}
    with httpx.Client(timeout=240.0) as client:
        resp = client.post(RUN_SYNC_URL, params=params, json=input_payload)

    if resp.status_code == 401:
        print("ERROR: 401 Unauthorized. Bad APIFY_TOKEN.", file=sys.stderr)
        sys.exit(4)
    if resp.status_code == 402:
        print("ERROR: 402 Payment required (out of Apify credit).", file=sys.stderr)
        sys.exit(7)
    if resp.status_code == 404:
        print(
            f"ERROR: 404 Actor not found at {ACTOR}.\n"
            "  Check https://apify.com/apidojo/tweet-scraper or update ACTOR in this script.",
            file=sys.stderr,
        )
        sys.exit(8)
    if resp.status_code >= 400:
        print(f"ERROR: HTTP {resp.status_code}\n{resp.text[:800]}", file=sys.stderr)
        sys.exit(6)

    data = resp.json()
    if isinstance(data, dict) and "data" in data:
        # Some Apify responses wrap items; normalize to a list.
        data = data["data"]
    return data if isinstance(data, list) else []


def normalize(t: dict[str, Any]) -> dict[str, Any]:
    """Shape an Apify tweet-scraper item into a common print-ready dict."""
    author = t.get("author") or {}
    return {
        "id": t.get("id") or t.get("conversationId") or "",
        "author_handle": "@" + (author.get("userName") or author.get("screen_name") or "unknown"),
        "author_name": author.get("name", ""),
        "verified": bool(author.get("isBlueVerified") or author.get("isVerified")),
        "created_at": t.get("createdAt") or t.get("created_at") or "",
        "text": (t.get("text") or t.get("fullText") or "").strip(),
        "likes": int(t.get("likeCount") or t.get("favouriteCount") or 0),
        "retweets": int(t.get("retweetCount") or 0),
        "replies": int(t.get("replyCount") or 0),
        "quotes": int(t.get("quoteCount") or 0),
        "url": t.get("url") or t.get("twitterUrl") or "",
    }


def render(tweets: list[dict[str, Any]], symbol: str, sort_mode: str, limit: int, hours: int) -> None:
    rows = [normalize(t) for t in tweets]
    rows.sort(
        key=lambda r: r["likes"] if sort_mode == "likes" else (r["likes"] + 2 * r["retweets"]),
        reverse=True,
    )
    rows = rows[:limit]

    print(f"Provider : apify ({ACTOR})")
    print(f"Symbol   : {symbol.upper()}")
    print(f"Window   : last {hours}h")
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
        description="Fetch top-liked X posts about a crypto via Apify tweet-scraper.",
    )
    parser.add_argument("symbol", help="Crypto symbol, e.g. BTC, ETH, SOL")
    parser.add_argument("--limit", type=int, default=5, help="Top tweets to show (default 5)")
    parser.add_argument("--hours", type=int, default=24, help="Lookback window in hours (default 24)")
    parser.add_argument(
        "--min-faves",
        type=int,
        default=0,
        help="Server-side filter: only tweets with >= this many likes",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=50,
        help="How many tweets the actor should scrape (costs scale with this)",
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
    tweets = fetch(args.symbol, args.hours, lang, args.min_faves, args.max_items)

    if args.json:
        rows = [normalize(t) for t in tweets]
        rows.sort(
            key=lambda r: r["likes"]
            if args.sort == "likes"
            else (r["likes"] + 2 * r["retweets"]),
            reverse=True,
        )
        out = {
            "provider": "apify",
            "actor": ACTOR,
            "symbol": args.symbol.upper(),
            "hours": args.hours,
            "sort": args.sort,
            "tweets": rows[: args.limit],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        render(tweets, args.symbol, args.sort, args.limit, args.hours)


if __name__ == "__main__":
    main()
