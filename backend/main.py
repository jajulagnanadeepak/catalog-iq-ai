"""
CatalogIQ AI — FastAPI application entry point.

Starts the API server with:
- CORS for Vite dev server (localhost:5173)
- MongoDB Atlas connection lifecycle
- Versioned router at /api
- Swagger UI at /docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database.connection import connect_db, close_db

from api.v1 import products, search, intent, recommend, auth
from routes import semantic_search, copilot


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


def create_app() -> FastAPI:

    app = FastAPI(
        title="CatalogIQ AI API",
        description="AI-powered commerce intelligence API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ---------------- CORS ----------------

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------- ROUTERS ----------------

    PREFIX = "/api"

    app.include_router(products.router, prefix=PREFIX)
    app.include_router(search.router, prefix=PREFIX)
    app.include_router(intent.router, prefix=PREFIX)
    app.include_router(recommend.router, prefix=PREFIX)
    app.include_router(auth.router, prefix=PREFIX)

    # Semantic Search Router
    app.include_router(semantic_search.router, prefix=PREFIX)
    # AI Copilot Router
    app.include_router(copilot.router, prefix=PREFIX)

    # ---------------- HEALTH ----------------

    @app.get("/health", tags=["Health"])
    async def health():
        return {
            "status": "ok",
            "version": app.version,
        }

    return app


app = create_app()