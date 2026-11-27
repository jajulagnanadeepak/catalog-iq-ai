"""
CatalogIQ AI — FastAPI application entry point.

Starts the API server with:
- CORS for Vite dev server (localhost:5173)
- MongoDB Atlas connection lifecycle
- Versioned router at /api
- Swagger UI at /docs
- Health probes: /health (legacy), /health/live, /health/ready
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database.connection import connect_db, close_db, get_database
from search import (
    SearchUnavailableError,
    get_search_engine,
    load_search_engine,
)
from services.session_intent_service import session_intent_service

from api.v1 import (
    products,
    search,
    intent,
    recommend,
    auth,
    budget_optimizer,
)
from routes import (
    semantic_search,
    copilot,
    visual_search,
    stylist,
    seasonal,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("catalogiq")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    await session_intent_service._ensure_indexes()

    # Load the semantic search model + FAISS index once, off the event loop.
    # A missing index no longer prevents startup; /health/ready reports it.
    engine = await asyncio.to_thread(load_search_engine)
    if not engine.ready:
        logger.error("Semantic search unavailable: %s", engine.error)

    try:
        yield
    finally:
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
    app.include_router(stylist.router, prefix=PREFIX)
    app.include_router(seasonal.router, prefix=PREFIX)
    app.include_router(visual_search.router, prefix=PREFIX)
    app.include_router(budget_optimizer.router, prefix=PREFIX)

    # Semantic Search Router
    app.include_router(semantic_search.router, prefix=PREFIX)
    # AI Copilot Router
    app.include_router(copilot.router, prefix=PREFIX)

    # ---------------- ERRORS ----------------

    @app.exception_handler(SearchUnavailableError)
    async def search_unavailable_handler(
        request: Request, exc: SearchUnavailableError
    ):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Semantic search is temporarily unavailable.",
            },
        )

    # ---------------- HEALTH ----------------

    @app.get("/health", tags=["Health"])
    async def health():
        # Unchanged legacy response (used by existing clients).
        return {
            "status": "ok",
            "version": app.version,
        }

    @app.get("/health/live", tags=["Health"])
    async def health_live():
        """Process is up. Does not touch dependencies."""
        return {"status": "ok", "version": app.version}

    @app.get("/health/ready", tags=["Health"])
    async def health_ready():
        """Dependencies are usable: MongoDB reachable and search loaded."""
        checks: dict = {}
        ready = True

        try:
            db = get_database()
            await db.command("ping")
            catalog_count = await db["catalog_products"].estimated_document_count()
            checks["mongodb"] = {"ok": True, "catalog_products": catalog_count}
            if catalog_count == 0:
                checks["mongodb"]["warning"] = (
                    "catalog_products is empty - check DATABASE_NAME"
                )
        except Exception as exc:  # noqa: BLE001
            ready = False
            checks["mongodb"] = {"ok": False, "error": type(exc).__name__}

        search_status = get_search_engine().status()
        checks["semantic_search"] = {
            "ok": search_status["ready"],
            **search_status,
        }
        if not search_status["ready"]:
            ready = False

        return JSONResponse(
            status_code=200 if ready else 503,
            content={
                "status": "ready" if ready else "not_ready",
                "version": app.version,
                "environment": settings.app_env,
                "checks": checks,
            },
        )

    return app


app = create_app()