# CatalogIQ AI — FastAPI Backend

AI-powered commerce intelligence API.

## Quick Start

### 1. Prerequisites
- **Python 3.11** (the version CI targets)
- MongoDB Atlas cluster (or local MongoDB)
- About 3 GB free RAM for the embedding model, FAISS index and (on first visual search) CLIP

### 2. Setup

```bash
cd backend

# Create and activate a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate          # Windows

pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt

# Environment file
cp .env.example .env               # Windows: copy .env.example .env
# Edit .env: MONGODB_URL, DATABASE_NAME (exact, case-sensitive), JWT_SECRET
```

### 3. Data and search index

The H&M catalog (105,542 articles, **demo data only**) lives in the
`catalog_products` collection. The semantic search index is a generated
artefact and is not in git (`hm_products.index`, `hm_product_ids.pkl`).

> ⚠️ `python -m database.import_hm_catalog` **deletes every document in
> `catalog_products`** and re-imports `articles.csv`. Do **not** run it against
> a database that already holds the catalog. A guarded, dry-run-first version
> is planned in Phase 1 (WS-E).

If the catalog is already in MongoDB, build the index only (reads the DB, writes local files):

```bash
python create_hm_embeddings.py
```

### 4. Start the API server

```bash
uvicorn main:app --reload --port 8000
```

The API starts even if the search index is missing; semantic search then
returns `503` and readiness reports why.

### 5. Health checks

| Endpoint | Meaning |
|---|---|
| `GET /health` | Legacy liveness response (unchanged) |
| `GET /health/live` | Process is up |
| `GET /health/ready` | MongoDB reachable, `catalog_products` count, search index loaded. `503` if not ready |

If `/health/ready` shows `catalog_products: 0`, `DATABASE_NAME` is almost certainly wrong.

### 6. Tests

```bash
pytest -q tests test_auth.py test_copilot_validation.py \
  test_intent_event_validation.py test_recommendation_filtering.py \
  test_semantic_reranker_relevance.py
```

These use in-memory fakes or mocks: no MongoDB, network or index needed.

> ⚠️ Do not run a bare `pytest` yet. Some legacy root scripts named `test_*.py`
> (for example `test_budget.py`, `test_config.py`) connect to the database or
> print configuration when collected. They will be moved to `scripts/` in
> Phase 1 WS-E.

### 7. Swagger UI

Open **http://localhost:8000/docs** in your browser.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/products` | List/filter/paginate products |
| `GET` | `/api/products/{id}` | Single product detail |
| `POST` | `/api/search` | Keyword product search |
| `GET` | `/api/recommend` | Top-rated recommendations |
| `POST` | `/api/intent` | NLU intent classification |
| `POST` | `/api/auth/signup` | Create account → JWT |
| `POST` | `/api/auth/login` | Login → JWT |
| `GET` | `/health`, `/health/live`, `/health/ready` | Health probes |

All routes are prefixed with `/api` to match the Vite dev proxy and frontend `requestWithFallback`.

---

## Folder Structure

```
backend/
├── main.py               # FastAPI app factory
├── config.py             # Pydantic-settings (reads .env)
├── dependencies.py       # DI: get_db, JWT auth guards
├── api/v1/               # Route handlers (thin controllers)
│   ├── products.py
│   ├── search.py
│   ├── intent.py
│   ├── recommend.py
│   └── auth.py
├── services/             # Business logic
│   ├── product_service.py
│   ├── search_service.py
│   ├── intent_service.py
│   └── recommendation_service.py
├── models/               # Pydantic schemas & DB models
│   ├── product.py
│   ├── user.py
│   └── schemas.py
├── database/             # MongoDB connection + seed
│   ├── connection.py
│   └── seed.py
├── utils/                # JWT, security, pagination
│   ├── jwt.py
│   ├── security.py
│   └── pagination.py
├── agents/               # Placeholder — future AI agents
└── embeddings/           # Placeholder — future embedding models
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MONGODB_URL` | `mongodb://localhost:27017` | MongoDB Atlas connection string |
| `DATABASE_NAME` | `CatalogIQ` | Database name (case-sensitive; must match Atlas exactly) |
| `JWT_SECRET` | dev placeholder | ≥32 chars; required outside development |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_EXPIRE_MINUTES` | `1440` | Token lifetime (24h) |
| `APP_ENV` | `development` | `development`/`test` allow dev defaults; anything else enforces a strong `JWT_SECRET` |
| `ALLOWED_ORIGINS` | localhost dev ports | Comma-separated CORS origins |
