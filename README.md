# Crypto Sentiment

A FastAPI + Vue 3 application for visualizing top cryptocurrency prices alongside the hottest X (Twitter) posts.

Stage 1 (current):

- Add a "case" by picking from the top 10 cryptocurrencies
- Each case becomes a panel showing a 24h, 15-minute resolution price line chart (Binance data)
- A "Fetch X posts" button pulls the top 5 hottest posts (mocked for now) for that crypto
- Post timestamps appear as markers overlaid on the price chart, with stacked offsets when timestamps collide
- Posts and chart markers are bidirectionally highlighted on click

## Screenshot

Two cases (BTC and SOL) tracking 24h price action with their top X posts pulled in. Orange dots on the chart mark the post timestamps; clicking a post highlights its dot, and vice versa.

![Crypto Sentiment dashboard](images/img.png)

## Stack

- Backend: Python 3.11, FastAPI, SQLAlchemy 2 (async), asyncpg, Alembic, httpx
- Frontend: Vue 3 + Vite + TypeScript, Element Plus, ECharts (vue-echarts), Pinia, Axios
- DB: PostgreSQL 16 (via docker compose)

## Quick start

```bash
# 1. Start Postgres
docker compose up -d postgres

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
pnpm install   # or npm install / yarn install
pnpm dev
```

- API docs: http://localhost:8000/docs
- Web app: http://localhost:5173

## Project layout

```
backend/   FastAPI service (routes, services, models, alembic)
frontend/  Vue 3 SPA (Element Plus + ECharts)
docker-compose.yml  Postgres for local dev
```

## Roadmap

- Replace `MockXPostsProvider` with a real X data source
- Add authentication and per-user `user_id`
- Stream realtime klines via Binance WebSocket
- Run sentiment analysis on posts and color-code scatter markers by sentiment
