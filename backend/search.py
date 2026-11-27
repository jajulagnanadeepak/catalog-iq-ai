"""
Semantic search over the H&M catalog (Sentence-Transformers + FAISS).

Behaviour is unchanged from the original module: the same model, the same
index files and the same `semantic_search(query, top_k)` signature and
result shape.

What changed (Phase 1, WS-A):
- The model and index are no longer loaded at import time. Importing this
  module (and therefore the whole API) no longer crashes or blocks when the
  index files are missing. `load_search_engine()` is called from the FastAPI
  lifespan; scripts that import `semantic_search` directly still work because
  the first call loads lazily.
- Missing artefacts raise `SearchUnavailableError`, which the API maps to a
  503 response, and `/health/ready` reports the reason.
- Model encoding and FAISS search run in a worker thread so they no longer
  block the event loop.
"""

from __future__ import annotations

import asyncio
import logging
import pickle
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from database.connection import get_database


logger = logging.getLogger("catalogiq.search")

MODEL_NAME = "all-MiniLM-L6-v2"
BASE_DIR = Path(__file__).resolve().parent

INDEX_PATH = BASE_DIR / "hm_products.index"
IDS_PATH = BASE_DIR / "hm_product_ids.pkl"


class SearchUnavailableError(RuntimeError):
    """Raised when the semantic search engine cannot serve requests."""


@dataclass
class SearchEngine:
    model: Any = None
    index: Any = None
    product_ids: list = field(default_factory=list)
    error: str | None = None
    warning: str | None = None

    @property
    def ready(self) -> bool:
        return self.model is not None and self.index is not None

    def status(self) -> dict:
        return {
            "ready": self.ready,
            "model": MODEL_NAME,
            "vectors": int(self.index.ntotal) if self.index is not None else 0,
            "product_ids": len(self.product_ids),
            "error": self.error,
            "warning": self.warning,
        }


_engine = SearchEngine()
_load_lock = threading.Lock()


def get_search_engine() -> SearchEngine:
    return _engine


def load_search_engine(
    index_path: Path | None = None,
    ids_path: Path | None = None,
) -> SearchEngine:
    """
    Load the embedding model, FAISS index and ID map once.

    Never raises: failures are recorded in `engine.error` so the API can still
    start and report the problem via /health/ready.
    """
    index_path = Path(index_path or INDEX_PATH)
    ids_path = Path(ids_path or IDS_PATH)

    with _load_lock:
        if _engine.ready:
            return _engine

        # Check cheap preconditions first so a missing index never triggers a
        # model download.
        missing = [str(p.name) for p in (index_path, ids_path) if not p.exists()]
        if missing:
            _engine.error = (
                "Search artefacts not found: "
                + ", ".join(missing)
                + ". Run `python create_hm_embeddings.py` (see backend/README.md)."
            )
            logger.error(_engine.error)
            return _engine

        try:
            import faiss
            from sentence_transformers import SentenceTransformer

            logger.info("Loading FAISS index from %s", index_path.name)
            index = faiss.read_index(str(index_path))

            # The ID map is a self-built artefact; never load pickles from
            # untrusted sources.
            with open(ids_path, "rb") as f:
                product_ids = pickle.load(f)

            if index.ntotal != len(product_ids):
                # Previous behaviour tolerated this (out-of-range rows are
                # skipped per query), so warn instead of refusing to serve.
                _engine.warning = (
                    f"Index/ID map size mismatch: {index.ntotal} vectors vs "
                    f"{len(product_ids)} ids. Rebuild the index."
                )
                logger.warning(_engine.warning)

            logger.info("Loading embedding model %s", MODEL_NAME)
            model = SentenceTransformer(MODEL_NAME)

        except Exception as exc:  # noqa: BLE001 - recorded and surfaced via health
            _engine.error = f"{type(exc).__name__}: {exc}"
            logger.exception("Failed to load search engine")
            return _engine

        _engine.model = model
        _engine.index = index
        _engine.product_ids = list(product_ids)
        _engine.error = None

        logger.info(
            "Search engine ready: %s vectors, %s ids",
            f"{index.ntotal:,}",
            f"{len(product_ids):,}",
        )
        return _engine


def _ensure_ready() -> SearchEngine:
    engine = _engine if _engine.ready else load_search_engine()
    if not engine.ready:
        raise SearchUnavailableError(
            engine.error or "Semantic search engine is not loaded."
        )
    return engine


def _encode_and_search(engine: SearchEngine, query: str, top_k: int):
    query_embedding = engine.model.encode(
        [query],
        convert_to_numpy=True,
    ).astype(np.float32)

    return engine.index.search(query_embedding, top_k)


async def semantic_search(query: str, top_k: int = 20):
    if not query or not query.strip():
        return []

    engine = _ensure_ready()

    top_k = max(1, min(top_k, engine.index.ntotal))

    # CPU-bound work off the event loop.
    distances, indices = await asyncio.to_thread(
        _encode_and_search, engine, query, top_k
    )

    product_ids = engine.product_ids

    article_ids = []

    for idx in indices[0]:
        if idx < 0 or idx >= len(product_ids):
            continue

        article_ids.append(product_ids[idx])

    if not article_ids:
        return []

    db = get_database()
    collection = db["catalog_products"]

    products = await collection.find(
        {
            "_id": {
                "$in": article_ids
            }
        }
    ).to_list(length=top_k)

    product_map = {
        product["_id"]: product
        for product in products
    }

    results = []

    for rank, (idx, distance) in enumerate(
        zip(indices[0], distances[0]),
        start=1,
    ):
        if idx < 0 or idx >= len(product_ids):
            continue

        article_id = product_ids[idx]

        product = product_map.get(article_id)

        if product is None:
            continue

        product["_id"] = str(product["_id"])

        results.append(
            {
                "rank": rank,
                "article_id": article_id,
                "distance": float(distance),
                "product": product,
            }
        )

    return results
