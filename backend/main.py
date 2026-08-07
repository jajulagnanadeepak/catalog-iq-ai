"""
CatalogIQ AI — FastAPI application entry point.

Starts the API server with:
- CORS for Vite dev server (localhost:5173)
- MongoDB Atlas connection lifecycle
- Versioned router at /api/v1
- Swagger UI at /docs, ReDoc at /redoc
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database.connection import connect_db, close_db
from api.v1 import products, search, intent, recommend, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage MongoDB connection lifecycle (FastAPI lifespan events)."""
    await connect_db()
    yield
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="CatalogIQ AI API",
        description=(
            "AI-powered commerce intelligence API for CatalogIQ AI. "
            "Provides semantic search, personalised recommendations, "
            "intent classification, and AI-driven catalog discovery."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    # All routes are mounted under /api so Vite can proxy /api → this server.
    PREFIX = "/api"
    app.include_router(products.router, prefix=PREFIX)
    app.include_router(search.router, prefix=PREFIX)
    app.include_router(intent.router, prefix=PREFIX)
    app.include_router(recommend.router, prefix=PREFIX)
    app.include_router(auth.router, prefix=PREFIX)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], summary="Health check")
    async def health():
        return {"status": "ok", "version": app.version}

    return app


app = create_app()
