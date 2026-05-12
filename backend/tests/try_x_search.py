"""Manual exploration script: fetch the top-liked X posts about a crypto
within the last N hours (default 24h).

Reads the Bearer Token from either:
  1. ``backend/.env`` file (key ``X_BEARER_TOKEN``), or
  2. a shell env var ``X_BEARER_TOKEN`` (or ``X_API_BEARER_TOKEN``).

Shell env var takes priority if both are set.

Uses the official X API v2 ``/2/tweets/search/recent`` endpoint (Basic tier).

Why this script does the sorting itself
---------------------------------------
The recent-search endpoint does NOT have a "sort by likes" parameter — its
``sort_order`` only supports ``relevancy`` or ``recency``. The query
operators ``min_faves:`` / ``min_retweets:`` are restricted to Pro and above.

So this script:
  1. fetches a wide pool of candidates from the last ``--hours`` (paginating
     up to ``--pages`` pages of 100 tweets each),
  2. sorts them locally by ``public_metrics.like_count`` (or
     ``--sort engagement`` for likes + 2*retweets), and
  3. returns the top ``--limit`` tweets.

Examples
--------
    cd backend
    source .venv/bin/activate

    python tests/try_x_search.py BTC                # top 5 liked in last 24h
    python tests/try_x_search.py ETH --limit 10
    python tests/try_x_search.py DOGE --hours 6     # last 6 hours
    python tests/try_x_search.py SOL --pages 3      # scan more candidates
    python tests/try_x_search.py BTC --sort engagement
    python tests/try_x_search.py XRP --lang none    # any language
    python tests/try_x_search.py BTC --json | jq .  # raw, post-sort

    # without activating the venv:
    .venv/bin/python tests/try_x_search.py SOL
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

# Resolve <repo>/backend/.env regardless of where the script is invoked from.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"
# ``override=False`` so a shell-exported X_BEARER_TOKEN wins over .env, which
# is the common convention for development workflows.
load_dotenv(_ENV_FILE, override=False)

X_API_URL = "https://api.x.com/2/tweets/search/recent"

# Cashtag (e.g. $BTC) requires Pro tier. Free / Basic users get a fallback that
# only relies on hashtags and plain keywords, which works on the Basic tier.
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


def get_token() -> str:
    token = os.environ.get("X_BEARER_TOKEN") or os.environ.get("X_API_BEARER_TOKEN")
    if not token:
        print(
            "ERROR: X_BEARER_TOKEN is not set.\n"
            f"  Tried .env file at: {_ENV_FILE}\n"
            "    (add a line:  X_BEARER_TOKEN=your_bearer_token_here)\n"
            "  Or export in your shell:\n"
            "    export X_BEARER_TOKEN='your_bearer_token_here'",
            file=sys.stderr,
        )
        sys.exit(2)
    return token


def build_query(symbol: str, lang: str | None) -> str:
    base = SYMBOL_QUERIES.get(symbol.upper(), f"#{symbol.upper()} -is:retweet")
    if lang:
        base = f"{base} lang:{lang}"
    return base


def _handle_http_error(resp: httpx.Response) -> None:
    if resp.status_code == 401:
        print("ERROR: 401 Unauthorized. Bearer token is wrong or expired.", file=sys.stderr)
        sys.exit(4)
    if resp.status_code == 403:
        print(
            "ERROR: 403 Forbidden. Your X developer tier likely doesn't include\n"
            "       /2/tweets/search/recent (need Basic or higher).",
            file=sys.stderr,
        )
        sys.exit(5)
    if resp.status_code == 429:
        reset = resp.headers.get("x-rate-limit-reset")
        remaining = resp.headers.get("x-rate-limit-remaining")
        print(
            f"ERROR: 429 Rate limited. remaining={remaining} reset_at_epoch={reset}",
            file=sys.stderr,
        )
        sys.exit(3)
    if resp.status_code >= 400:
        print(f"ERROR: HTTP {resp.status_code}\n{resp.text}", file=sys.stderr)
        sys.exit(6)


def fetch_window(
    symbol: str,
    hours: int,
    lang: str | None,
    pages: int,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], str]:
    """Fetch up to ``pages * 100`` candidate tweets in the last ``hours``.

    Returns (tweets, users_by_id, query) where tweets are the raw API tweet
    objects (sort_order=relevancy from X) and users_by_id is keyed by author_id.
    Sorting by likes is performed by the caller.
    """
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "crypto-sentiment-dev/0.1"}
    query = build_query(symbol, lang)

    # X expects RFC3339 UTC timestamps, e.g. 2026-05-12T10:00:00Z.
    # The recent-search endpoint only goes back ~7 days; we stay well within that.
    start_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    base_params: dict[str, Any] = {
        "query": query,
        "max_results": 100,
        "start_time": start_time,
        "tweet.fields": "created_at,public_metrics,author_id,lang",
        "expansions": "author_id",
        "user.fields": "username,name,verified",
        # 'relevancy' tends to surface more popular tweets than 'recency'.
        # We still re-sort locally by likes below.
        "sort_order": "relevancy",
    }

    all_tweets: list[dict[str, Any]] = []
    users_by_id: dict[str, dict[str, Any]] = {}
    next_token: str | None = None

    with httpx.Client(timeout=15.0) as client:
        for page_idx in range(pages):
            params = dict(base_params)
            if next_token:
                params["next_token"] = next_token
            resp = client.get(X_API_URL, headers=headers, params=params)
            _handle_http_error(resp)
            payload = resp.json()
            page_tweets = payload.get("data", []) or []
            all_tweets.extend(page_tweets)
            for u in payload.get("includes", {}).get("users", []) or []:
                users_by_id[u["id"]] = u
            next_token = (payload.get("meta") or {}).get("next_token")
            if not next_token or not page_tweets:
                break
            # Gentle pacing to avoid bursting into rate limits on Basic tier.
            if page_idx < pages - 1:
                time.sleep(1.0)

    return all_tweets, users_by_id, query


def sort_tweets(tweets: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    def key_likes(t: dict[str, Any]) -> int:
        return int((t.get("public_metrics") or {}).get("like_count", 0))

    def key_engagement(t: dict[str, Any]) -> int:
        m = t.get("public_metrics") or {}
        return (
            int(m.get("like_count", 0))
            + 2 * int(m.get("retweet_count", 0))
            + int(m.get("reply_count", 0))
            + int(m.get("quote_count", 0))
        )

    def key_recency(t: dict[str, Any]) -> str:
        return t.get("created_at") or ""

    keyfn = {"likes": key_likes, "engagement": key_engagement, "recency": key_recency}[mode]
    return sorted(tweets, key=keyfn, reverse=True)


def render_pretty(
    tweets: list[dict[str, Any]],
    users_by_id: dict[str, dict[str, Any]],
    query: str,
    hours: int,
    scanned: int,
    sort_mode: str,
) -> None:
    print(f"Query    : {query}")
    print(f"Window   : last {hours}h")
    print(f"Scanned  : {scanned} candidate tweets")
    print(f"Sorted by: {sort_mode}")
    print(f"Showing  : top {len(tweets)}")
    print("-" * 80)

    if not tweets:
        print("No tweets returned. Try --lang none, a different symbol, or a longer --hours.")
        return

    for i, tw in enumerate(tweets, 1):
        user = users_by_id.get(tw.get("author_id"), {})
        author = "@" + user.get("username", "unknown")
        name = user.get("name", "")
        verified = " [verified]" if user.get("verified") else ""
        when = tw.get("created_at", "?")
        m = tw.get("public_metrics") or {}
        text = (tw.get("text") or "").replace("\n", " ").strip()
        print(f"\n[{i}] {author}{verified}  ({name})  {when}")
        print(
            f"    likes={m.get('like_count', 0)}  "
            f"retweets={m.get('retweet_count', 0)}  "
            f"replies={m.get('reply_count', 0)}  "
            f"quotes={m.get('quote_count', 0)}"
        )
        print(f"    {text}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch top-liked X posts about a cryptocurrency from the last N hours.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("symbol", help="Crypto symbol, e.g. BTC, ETH, SOL")
    parser.add_argument("--limit", type=int, default=5, help="How many top tweets to show (default 5)")
    parser.add_argument("--hours", type=int, default=24, help="Lookback window in hours (default 24)")
    parser.add_argument(
        "--pages",
        type=int,
        default=1,
        help="How many pages of 100 tweets to scan (default 1, max 5)",
    )
    parser.add_argument(
        "--sort",
        choices=["likes", "engagement", "recency"],
        default="likes",
        help="Local sort order applied to the candidate pool (default 'likes')",
    )
    parser.add_argument(
        "--lang",
        default="en",
        help="Language filter (e.g. 'en', 'zh'). Use 'none' to disable.",
    )
    parser.add_argument("--json", action="store_true", help="Print raw post-sort JSON")
    args = parser.parse_args()

    lang = None if args.lang.lower() == "none" else args.lang
    pages = max(1, min(5, args.pages))

    candidates, users_by_id, query = fetch_window(
        symbol=args.symbol, hours=args.hours, lang=lang, pages=pages
    )
    ranked = sort_tweets(candidates, args.sort)
    top = ranked[: args.limit]

    if args.json:
        out = {
            "query": query,
            "hours": args.hours,
            "scanned": len(candidates),
            "sort": args.sort,
            "tweets": [
                {
                    **t,
                    "author": users_by_id.get(t.get("author_id"), {}),
                }
                for t in top
            ],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        render_pretty(top, users_by_id, query, args.hours, len(candidates), args.sort)


if __name__ == "__main__":
    main()
