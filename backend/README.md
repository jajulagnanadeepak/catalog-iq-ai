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

> ⚠️ `python -m database.import_hm_catalog` is a **dry run** by default: it
> validates `articles.csv` and reports the plan without changing anything.
> `--apply` imports into an empty `catalog_products`. If the collection already
> holds documents, a real run **deletes every one of them** and re-imports the
> CSV; that needs `--apply --i-understand-this-replaces-catalog` plus typing
> `yes` at the prompt. `APP_ENV=production` is refused unless you also pass
> `--allow-production`. Do **not** replace a catalog you still need.

If the catalog is already in MongoDB, build the index only (reads the DB, writes local files):

```bash
python create_hm_embeddings.py           # dry run: reports the plan and the current artefacts
python create_hm_embeddings.py --apply   # first build
python create_hm_embeddings.py --apply --i-understand-this-overwrites-index   # rebuild
```

The artefacts are written next to `create_hm_embeddings.py` (where `search.py`
loads them), first as `*.tmp` files that are validated before replacing the live
pair; the previous pair is kept as `*.bak`. `APP_ENV=production` is refused
unless you also pass `--allow-production`.

`create_hm_embeddings.py` is the only supported embedding builder. The legacy
`create_embeddings.py` (which built `products.index` / `product_ids.pkl` from
the old `Products` collection, files `search.py` never loads) was retired in
Phase 1 WS-E3.4; git history keeps it.

The 12 demo products (`p-001` to `p-012`, the `products` collection used by
product pages, recommendations, budget, stylist and visual search) come from
`database/seed.py`:

```bash
python -m database.seed            # dry run: database name, existing count, planned insert
python -m database.seed --apply    # insert, only if `products` is empty
```

It never updates, deletes or overwrites documents; a non-empty collection is
left untouched. `APP_ENV=production` is always refused (no override).

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
pytest -q tests
```

All backend tests live in `backend/tests/`. They use in-memory fakes or mocks:
no MongoDB, network or index needed. Run pytest from `backend/`: from the
repository root `backend/pytest.ini` is not applied, so nothing unsafe is
collected but async tests without an explicit `@pytest.mark.asyncio` (which
rely on `asyncio_mode = auto`) fail with "async def functions are not natively
supported".

> The legacy manual scripts that used to be named `test_*.py` (`test_budget.py`
> was collected as a test and called MongoDB and the exchange-rate API) now live
> in `scripts/` with non-`test_` names, so pytest no longer collects them
> (Phase 1 WS-E, step E1). `manual_budget_search` and
> `manual_multicurrency_budget` use MongoDB and the exchange-rate API,
> `manual_exchange_rates` uses the exchange-rate API, and
> `manual_intent_detection` uses neither. Run one deliberately from `backend/`
> with `python -m scripts.<name>`, for example
> `python -m scripts.manual_intent_detection`. A bare `pytest` run from
> `backend/` collects only `tests/`. (`tests/test_config.py` used to print the
> MongoDB URL and JWT secret; it is now a plain assertion test that prints
> nothing.)

#### Diagnostic scripts (`scripts/`)

Read-only checks, moved out of the backend root in Phase 1 WS-E (step E2b).
They write nothing, but most need your `.env` (MongoDB) or the network, and
they are not part of the test suite. Run one deliberately from `backend/`:
`python -m scripts.<name>` (for example `python -m scripts.check_hm_catalog`).

| Script | Reads |
|---|---|
| `check_catalog` | MongoDB `products`: image fields of 15 products |
| `check_catalogs` | MongoDB `products` and `Products`: counts and one sample each |
| `check_hm_catalog` | MongoDB `catalog_products`: count and one sample |
| `check_image_urls` | MongoDB `products`, then an HTTP GET of every image URL |
| `check_search_relevance` | FAISS index + MongoDB `catalog_products`; loads the embedding model (may download it into the model cache) |
| `check_trousers` | MongoDB `products` (via `ProductService`) |
| `check_trousers_budget` | MongoDB `products` + the exchange-rate API (via `BudgetService`) |

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
| `SEARCH_RERANK_VERSION` | `v1` | Semantic-search reranker: `v1` (baseline) or `v2` (S1 category vocabulary + S2 diversity backfill). Responses in v2 mode include `"rerank_version": "v2"` |
| `SEARCH_V2_KIDS_DOWNRANK` | `false` | v2 only (S4): children's products get a soft 0.10 score penalty for queries that aren't about children. Nothing is removed |
| `SEARCH_V2_ATTRIBUTE_BOOST` | `false` | v2 only (S3-lite): +0.25 for products whose name/description matches a pattern the query names (floral, striped, check, …), only when a category is detected; `navy` matches Dark Blue |
| `SEARCH_V2_OUT_OF_CATALOG` | `false` | v2 only (S5 hard tier): a query with no fashion category, no catalogue product-type/accessory phrase and an explicit unsupported-domain phrase (laptop, sofa, …) skips retrieval and returns `products: []`, `out_of_catalog: true`, `ooc_reason: "unsupported_domain:<domain>"` |
