# tests/

Manual exploration scripts that talk to real upstream services. These are not
unit tests — they exist so you can validate integrations end-to-end with your
own credentials before wiring them into the production code.

## Provider comparison

| Script                  | Provider           | Auth env var          | Notes                                                       |
| ----------------------- | ------------------ | --------------------- | ----------------------------------------------------------- |
| `try_x_search.py`       | Official X API v2  | `X_BEARER_TOKEN`      | Basic tier ($200/mo). No server-side likes sort.            |
| `try_twitterapi_io.py`  | twitterapi.io      | `TWITTERAPI_IO_KEY`   | ~$0.15 / 1k tweets. Supports full X query incl `min_faves:`. |
| `try_apify.py`          | Apify tweet-scraper | `APIFY_TOKEN`        | ~$0.40 / 1k. Free tier $5 monthly credit. Async actor run.   |

All three accept the same CLI shape:

```bash
python tests/<script>.py BTC                  # top 5 in last 24h
python tests/<script>.py ETH --limit 10
python tests/<script>.py BTC --hours 6
python tests/<script>.py BTC --sort engagement
python tests/<script>.py XRP --lang none
python tests/<script>.py BTC --json | jq .
```

The twitterapi.io and Apify variants also support:

```bash
--min-faves 500    # server-side: only tweets with >= 500 likes
```

## `try_x_search.py`

Fetches the **top-liked X (Twitter) posts about a crypto in the last N hours**
(default 24h). Uses the official X API v2 `/2/tweets/search/recent` endpoint
plus client-side sorting, because the endpoint itself doesn't support sorting
by likes (`sort_order` is only `relevancy` or `recency`; the `min_faves:`
operator is Pro/Enterprise-only).

The script:

1. Computes `start_time = now - --hours`.
2. Fetches up to `--pages * 100` candidate tweets (Basic tier allows 100 per
   page; we paginate with `next_token`, sleeping 1s between pages).
3. Sorts the pool locally by `--sort` (default `likes`).
4. Shows the top `--limit` (default 5).

### Prereqs

1. An X developer account with at least **Basic** tier (free tier does NOT
   include the recent search endpoint).
2. A Bearer Token from your X app's "Keys and tokens" page.

### Run

```bash
# 1. configure your token. EITHER edit backend/.env and add:
#       X_BEARER_TOKEN=your_bearer_token_here
#    OR export it in your shell:
#       export X_BEARER_TOKEN='your_bearer_token_here'
#    (shell export wins if both are present.)

# 2. activate the venv that has httpx + python-dotenv
cd backend
source .venv/bin/activate

# 3. run
python tests/try_x_search.py BTC                   # top 5 most-liked in last 24h
python tests/try_x_search.py ETH --limit 10        # top 10 instead
python tests/try_x_search.py DOGE --hours 6        # last 6 hours
python tests/try_x_search.py SOL --pages 3         # scan 300 candidates not 100
python tests/try_x_search.py BTC --sort engagement # likes + 2*retweets + replies + quotes
python tests/try_x_search.py XRP --lang none       # any language
python tests/try_x_search.py BTC --json | jq .     # raw post-sort JSON

# alternative without activating the venv:
.venv/bin/python tests/try_x_search.py BTC
```

### Supported symbols (curated queries)

BTC, ETH, BNB, SOL, XRP, ADA, DOGE, AVAX, DOT, TRX — anything else will fall
back to `#<SYMBOL> -is:retweet`.

### Expected output

```
Query    : (#Bitcoin OR #BTC OR Bitcoin) -is:retweet lang:en
Found    : 10 tweets (meta.result_count=10)
--------------------------------------------------------------------------------

[1] @someuser [verified]  (Some User)  2026-05-12T08:32:11.000Z
    likes=2401  retweets=311  replies=88  quotes=14
    BTC just reclaimed the 4h trend ...
```

### Common errors

| Code | Meaning                                                           |
| ---- | ----------------------------------------------------------------- |
| 401  | Bearer token is missing/wrong/expired.                            |
| 403  | Your dev tier doesn't include recent search. Upgrade to Basic+.   |
| 429  | Rate limited. Check the `x-rate-limit-reset` epoch in stderr.     |

### Notes on cashtags

The query `$BTC` (cashtag operator) is **Pro tier only**. This script avoids
cashtags by default so it works on the Basic tier. If you have Pro access,
edit `SYMBOL_QUERIES` and add `OR $BTC` etc.
