from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_cases import router as cases_router
from app.api.routes_cryptos import router as cryptos_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Crypto Sentiment API",
        version="0.1.0",
        description="Backend for crypto + X (Twitter) sentiment panels.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(cryptos_router, prefix="/api")
    app.include_router(cases_router, prefix="/api")
    return app


app = create_app()
