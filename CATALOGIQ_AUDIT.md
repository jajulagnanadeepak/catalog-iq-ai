# CatalogIQ AI — Production Readiness Audit (Master Report)

| | |
|---|---|
| **Repository** | `jajulagnanadeepak/catalog-iq-ai` |
| **Commit audited** | `5d7ba72` — "Fix frontend loading and improve CatalogIQ AI" (2026-10-19), 39 commits of history inspected |
| **Audit date** | 2026-11-27 |
| **Type** | Static, read-only audit. No application source, database, deployment setting or existing feature was modified. |

Companion documents: [Architecture](CATALOGIQ_ARCHITECTURE.md) · [UI/UX](CATALOGIQ_UI_UX_REVIEW.md) · [API](CATALOGIQ_API_REVIEW.md) · [AI](CATALOGIQ_AI_REVIEW.md) · [Security](CATALOGIQ_SECURITY_REVIEW.md) · [Roadmap](CATALOGIQ_IMPLEMENTATION_ROADMAP.md)

---

## 0. Scope, method and limits (read this first)

**What was done.** All 191 tracked files were inventoried. Every backend Python file, every frontend route, the API client/service layer, the cart/auth stores, configuration, tests, scripts and the full git history (secret-pattern scan) were read. Findings cite `file:line` from commit `5d7ba72`.

**What was NOT done — and therefore what this report cannot tell you:**

| Not done | Why | Consequence |
|---|---|---|
| Running the backend or its tests | Workspace has no network, so `fastapi`, `motor`, `faiss`, `sentence-transformers`, `torch` etc. could not be installed | Findings about runtime behaviour are from code reading. Three items are explicitly marked **UNVERIFIED** (see H-13) with a one-line check you can run. |
| Building/linting/running the frontend | No `node_modules`, no network | No bundle-size, Lighthouse or visual evidence. UI/UX findings are from source, not screenshots. |
| Touching MongoDB Atlas | No credentials supplied; instruction forbids touching production data | Collection contents, counts and indexes are inferred from import/seed scripts. **Whether `catalog_products` really holds 105,542 documents was not verified**; `articles.csv` does have 105,542 data rows (105,543 lines incl. header). |
| Measuring search relevance or latency | No models, index or data available | AI findings are about design risk and missing evaluation, not measured quality. No latency numbers are claimed. |
| Index files | `backend/hm_products.index` and `hm_product_ids.pkl` are git-ignored and were not provided | FAISS behaviour is from `create_hm_embeddings.py` and `search.py`. |

**Severity scale.** *Critical* = blocks launch or enables compromise/data loss with default configuration. *High* = serious defect or missing production requirement; fix before real customers. *Medium* = should be fixed in the hardening phase. *Low* = cleanup.

---

## 1. Executive summary

CatalogIQ AI today is a **well-built AI discovery demo with a convincing UI**, not yet an e-commerce platform. The semantic-search pipeline (Sentence-Transformers → FAISS → intent-aware rerank → session intent) is real, coherent and worth preserving. Auth basics (bcrypt, JWT, unit tests) are sound. The gap to "real customers can use it" is large and mostly structural:

1. **There is no commerce backend.** No cart, checkout, order, payment, inventory, role or admin code exists. The cart lives in `localStorage` and the **Checkout button does nothing** (C-04).
2. **The 105,542-product catalog cannot be sold.** The H&M import keeps only name/type/category/department/section/garment-group/colour/description — **no price, image, stock, rating or sizes** (C-03). Meanwhile almost every commerce endpoint reads a *different* 12-item demo collection (`products`), so search results and product pages are drawn from two unconnected datasets (C-02).
3. **The frontend hides failures with fabricated data.** On any API error it silently substitutes hard-coded mock products — including a fake visual-search result with invented similarity scores and a product page that shows the wrong product for an unknown ID (C-05). The dashboard, login page and landing page also show invented metrics (H-08).
4. **The backend cannot be installed from the repo as documented** — `requirements.txt` omits FAISS, Sentence-Transformers, PyTorch, Transformers, NumPy, Pandas and Pillow, and the app loads the model and index at import time from git-ignored files (C-01).
5. **Security defaults are unsafe** — default JWT secret `change-me-secret`, no rate limiting anywhere, unauthenticated expensive endpoints, no role model, no unique index on `users.email` (C-06, C-07, H-01, H-02, H-03).
6. **Gemini is not integrated.** It appears only in the README (H-06). The "AI Copilot" is a rule-based router with templated sentences.

**Count of findings:** 7 Critical · 14 High · 13 Medium · 8 Low.

**Preserve (do not rewrite):** the FAISS/MiniLM search pipeline and 105,542-row catalog source, intent/session-intent design with TTL index, multi-currency budget logic, auth module and its tests, the shadcn/ui component system, the API-mapping layer `mapApiProduct`, and visual-search upload validation. The roadmap is additive.

---

## 2. Technology stack — as found vs. as described

| Area | Described in your brief / README | Actually in repo |
|---|---|---|
| Frontend framework | React + Vite + TS; README adds React Router | **TanStack Start** (SSR, file-based routing, Nitro) on Vite 8 / React 19, wrapped by the Lovable config (`vite.config.ts`, `package.json`). No React Router. Package name is still `tanstack_start_ts`. |
| Styling/UI | Tailwind, shadcn/ui | Confirmed (Tailwind 4, Radix, ~50 shadcn components) |
| HTTP | Axios | Confirmed (`src/lib/api/client.ts`) |
| Backend | Python, FastAPI, REST | Confirmed (FastAPI 0.115, Motor 3.5) |
| Database | MongoDB Atlas | Confirmed; collections: `users`, `products`, `catalog_products`, `session_events` (+ legacy `Products` from root `seed.py`) |
| Embeddings / vector | Sentence Transformers, FAISS | Confirmed: `all-MiniLM-L6-v2`, `IndexFlatL2` |
| LLM | **Gemini** | **Not present in code, dependencies or config** (only `README.md:54`) |
| Visual search | listed | CLIP `openai/clip-vit-base-patch32` (not mentioned in brief) |
| Deployment | — | None: no Dockerfile, compose, CI, Procfile or hosting config |

---

## 3. Feature status matrix

Legend: ✅ working in code · 🟡 partial / demo-grade · ❌ absent.

| Capability | Status | Evidence / note |
|---|---|---|
| Semantic search (FAISS + rerank) | 🟡 | Real pipeline (`search.py`, `routes/semantic_search.py`, `services/semantic_reranker.py`). Max 10 results, no price/image data, filters/pagination are client-side (H-04). |
| Intent detection | 🟡 | Rule-based keyword matching with substring defects (M-01). Not LLM-based. |
| Session-intent tracking | ✅ | `session_intent_service.py`: TTL index, weighted events. Events are unauthenticated (H-03). |
| Product recommendations | 🟡 | `/api/recommend` scores first 100 in-stock docs of the 12-item collection (M-03). |
| AI Shopping Copilot | 🟡 | Rule router → templated sentences; stateless; no Gemini (H-06). |
| AI Stylist | 🟡 | Keyword scoring over ≤500 docs of `products`; unbounded cartesian product (M-05). |
| Budget Optimizer | 🟡 | Greedy allocator over `products` (≤500 docs). Logic is sound; data source is the demo set. |
| Budget-aware chat search + FX | ✅/🟡 | `budget_service.py` + Frankfurter FX; no caching (M-06). Reads 12-item collection. |
| Seasonal recommendations | 🟡 | Keyword rules over `products`. |
| Visual search | 🟡 | CLIP over first 100 of `products`, remote-fetched per request (C-07). |
| Landing page | 🟡 | Uses hard-coded mock products and invented claims (H-08). |
| Login / registration | ✅/🟡 | Works; no verification, reset, refresh, logout-revoke (H-14). |
| Profile | ✅ | `GET /auth/me`, `PUT /auth/profile`. |
| Dashboard | ❌ (fake) | Static numbers in `dashboard.tsx:37-52`. |
| Product listing / details | 🟡 | `/products` serves 12 demo items; detail 404s for semantic-search IDs → wrong product shown (C-02, C-05). |
| Shopping cart | 🟡 | Browser-only (`cart-wishlist.ts`). |
| **Checkout / orders / payments / inventory** | ❌ | No code anywhere. |
| **Admin interface / roles** | ❌ | No code anywhere. |
| Image storage | ❌ | Hot-linked Unsplash URLs; H&M rows have none. |
| Logging / monitoring / CI / deploy | ❌ | None. |

---

## 4. Findings register

Format: **ID · Title** — *Component* — **Evidence** — **Fix** — **Priority** (P0 = do first … P3 = later). Detailed treatment lives in the specialised documents named in brackets.

### 4.1 Critical

**C-01 · Backend cannot be installed or started from the repository as documented** `[Architecture, Security]`
- *Component:* `backend/requirements.txt`, `backend/main.py`, `backend/search.py`, `.gitignore`, `backend/README.md`
- *Evidence:*
  - `requirements.txt` is a UTF-16 LE file (BOM + CRLF; verified with `file`) listing 38 packages but **none** of `faiss`, `sentence-transformers`, `torch`, `transformers`, `numpy`, `pandas`, `pillow`, which the code imports (`search.py:5-6`, `routes/visual_search.py:7-11`, `database/import_hm_catalog.py:2`).
  - `main.py:28-34` imports `routes.semantic_search` → `search.py`, which at import time loads the SentenceTransformer and `faiss.read_index("hm_products.index")` (`search.py:18-27`). Those files are git-ignored (`.gitignore:53-54, 63-64`), so a fresh clone raises `FileNotFoundError` before the server starts. Importing `routes.visual_search` also pulls in `torch`/`transformers`.
  - `backend/README.md:29-39` documents only `python -m database.seed` (the 12-item set); it never mentions importing the 105,542-row catalog or building the index.
  - `services/semantic_reranker.py:1` imports `transformers.models.audio_spectrogram_transformer…` (unused, accidental).
- *Fix:* UTF-8 `requirements.txt` with every import, pinned (plus `requirements-dev.txt`); move model/index loading into the FastAPI `lifespan` with a clear startup error and a `/health/ready` check; document import → embed → serve; delete the stray import. Do **not** change the search algorithm.
- *Priority:* **P0**

**C-02 · Two disconnected product catalogs; commerce endpoints read the 12-item demo set** `[Architecture, API, AI]`
- *Component:* `services/product_service.py:20`, `api/v1/search.py`, `api/v1/recommend.py`, `budget_optimizer.py:43`, `routes/stylist.py:163`, `routes/seasonal.py:153`, `routes/visual_search.py:91` (all `db["products"]`) vs `search.py:61` (`catalog_products`)
- *Evidence:* `database/seed.py` inserts exactly 12 products with IDs `p-001…p-012`. `database/import_hm_catalog.py:11` loads the H&M rows into `catalog_products` with `_id = article_id`. Semantic search returns H&M IDs; `GET /api/products/{id}` looks only in `products` (`product_service.py:104-106`) → 404 → the frontend falls back to `PRODUCTS[0]` (`services.ts:213-216`), so **clicking a semantic-search result shows an unrelated product**. Separately, frontend mock IDs `p-001…p-012` (e.g. "Aurora Merino Overcoat", "Studio ANC Headphones") collide with the *different* seeded products of the same IDs ("Mercer Wool Overcoat", "Slim Taper Chino"), so a cart item can change identity depending on whether the backend is reachable.
- *Fix:* One canonical product collection and one ID scheme (additive migration; keep both source collections). Point every endpoint at it. See Roadmap Phase 1.
- *Priority:* **P0**

**C-03 · The 105,542-product catalog has no price, image, stock, rating, brand or sizes** `[Architecture, API, AI]`
- *Component:* `database/import_hm_catalog.py:57-70`, `create_hm_embeddings.py:44-57`
- *Evidence:* The imported document has exactly: `_id, article_id, name, product_type, category, department, section, garment_group, colour, description`. `articles.csv` itself carries no price/image columns. The frontend therefore maps `price` to `0` (`services.ts:258`), disables "Add to cart" when price ≤ 0 (`product-card.tsx:208`), and falls back to `brand = department` (`services.ts:254`).
- *Fix:* Decide the data source (a supplier/pricing feed, or clearly-labelled synthetic demo data — a **business decision** for you; see Roadmap §Decisions). Add the fields **additively** to a new canonical collection; never mutate `catalog_products` in place. Add `in_stock`/`stock_qty`, `price`, `currency`, `image` and `sku`.
- *Priority:* **P0**

**C-04 · No commerce backend: cart, checkout, orders, payments, inventory, roles, admin** `[Architecture, API, Security, UI/UX]`
- *Component:* whole repo; `src/components/cart/cart-sheet.tsx:167-176`; `src/lib/store/cart-wishlist.ts:15`; `utils/jwt.py`
- *Evidence:* Backend routers: products, search, intent, recommend, auth, stylist, seasonal, visual-search, budget, semantic-search, copilot. No `cart`/`checkout`/`orders`/`payments`/`admin`. The Checkout button's `onClick` only closes the sheet. JWT payload is `{sub, email, exp}` — no role. There is no `/checkout`, `/orders` or `/admin` frontend route. `session_events` accepts `event_type: "purchase"` but nothing creates purchases.
- *Fix:* Roadmap Phases 3 and 5 (server-side cart, order state machine, inventory reservation, payment gateway in **test mode only**, RBAC, admin console).
- *Priority:* **P0** (blocks "real customers can use it")

**C-05 · Silent mock-data fallback hides outages and fabricates content** `[UI/UX, API, Security]`
- *Component:* `src/lib/api/client.ts:30-41`; `src/lib/api/services.ts:185-208, 213-216, 388-440, 444-456, 462-567, 571-641, 683-713, 716-761`
- *Evidence:* `requestWithFallback` catches **every** error (network, 4xx, 5xx, validation), waits 450 ms and returns hard-coded data. Examples: unknown product ID → `PRODUCTS[0]`; recommendations fall back to invented reasons such as "Completes 3 of your saved looks." / "Colour-matched to your last two purchases."; visual search failure returns fake `detected: ["Apparel","Fashion","Pattern match"]` and fabricated similarity scores 0.92, 0.88…; budget and stylist silently compute on the mock list. The error UIs in `product.$productId.tsx:115`, `visual-search.tsx:124` are therefore unreachable for these calls.
- *Fix:* Remove fallbacks from production builds (gate behind an explicit `VITE_USE_MOCKS=true`, default off); surface real error states; never fabricate personalisation text.
- *Priority:* **P0**

**C-06 · Default JWT signing secret and no startup guard; no role claim** `[Security]`
- *Component:* `backend/config.py:31-34`, `utils/jwt.py`
- *Evidence:* `jwt_secret` defaults to `"change-me-secret"`; the app starts normally if `JWT_SECRET` is unset, making tokens forgeable by anyone who reads this public repo. `.env.example:6` carries a placeholder only (no real secret found in history — see Security §Secrets).
- *Fix:* Fail fast when `APP_ENV != development` and the secret is default/short (<32 bytes); add `iat`, `jti`, `role`; support key rotation.
- *Priority:* **P0**

**C-07 · Visual search can freeze the whole API and is not a catalog-wide search** `[AI, Security, API]`
- *Component:* `backend/routes/visual_search.py:61-165`
- *Evidence:* Per request, inside an `async def`: it loads up to 100 products (`MAX_CATALOG_IMAGES = 100`), downloads each image serially over HTTP (`:117-130`) and runs a CLIP forward pass for each on the event loop thread (`image_embedding`, synchronous torch). No caching of catalog embeddings, no download size cap, no auth, no rate limit. Only the first 100 documents of the 12-item `products` collection are ever considered — it cannot search the 105,542-item catalog.
- *Fix:* Precompute catalog image embeddings offline into a second FAISS index; keep only the *query* embedding at request time and run it off the event loop (`run_in_threadpool`); add auth/rate-limit and image-size/pixel caps.
- *Priority:* **P0**

### 4.2 High

**H-01 · No rate limiting or abuse protection** — *all routers; `main.py`.* No limiter/middleware exists (grep: no `slowapi`, `limiter`). Login can be brute-forced; `/copilot/chat`, `/semantic-search`, `/visual-search` are CPU-heavy. *Fix:* per-IP and per-user limits (login stricter), request-size limits, upstream WAF. **P1**

**H-02 · No unique index on `users.email`; no indexes/validators on `products`** — `api/v1/auth.py:32-51`, `database/*`. Signup does `find_one` then `insert_one`; the `DuplicateKeyError` handler is dead because no unique index is created anywhere (only `session_events` indexes are created, `session_intent_service.py:25-42`). Two concurrent signups can create duplicate accounts. `products` has no indexes for `category/price/rating` and no schema validator. *Fix:* startup index bootstrap (unique `users.email`, product indexes, JSON-schema validators in `moderate` mode). **P0**

**H-03 · No authorization model; unauthenticated event ingestion can poison personalisation** — `api/v1/intent.py:35-67`, all `routes/*`. Only `/auth/me` and `/auth/profile` require a token. Anyone can post `{"session_id": "<victim>", "event_type": "purchase"}` (weight 10) and skew another session's recommendations; `session_id` is a client-chosen string. *Fix:* bind session to an HttpOnly cookie/authenticated user; server-derive purchase events from real orders; drop `purchase` from the public event enum. **P1**

**H-04 · Search pagination and filters are not real** — `routes/semantic_search.py:22`, `src/routes/search.tsx:60`, `services.ts:289-385`. The frontend sends `{query, page, pageSize, …}` but the backend only reads `query/top_k/session_id`; `top_k` defaults to **10**. Filtering and sorting happen client-side on those ≤10 items, and `total` is the filtered length — so "matches" is at most 10 and pagination is cosmetic. `CATEGORIES` in the filter UI (`filters.tsx:13,47`; `mock.ts:209`) lists six demo categories that do not exist in H&M data (`product_group_name`), so selecting one returns nothing. *Fix:* server-side filters/pagination inside the retrieval stage; category facets sourced from the catalog. **P1**

**H-05 · Retrieval/rerank design risks with no relevance evaluation** `[AI]` — `semantic_reranker.py:68-80, 117-128`; `routes/semantic_search.py:72-75`. Hard category filter is applied *after* fetching 100 FAISS neighbours (low recall for "black top" when neighbours are mixed); final weights sum to **1.25** (0.40+0.15+0.35+0.10+0.10+0.15) so scores are not normalised; no labelled query set exists. *Fix:* build an evaluation set first (Roadmap Phase 4), then tune; push category/colour constraints into retrieval (over-fetch or filtered search). **P1**

**H-06 · Gemini is not integrated; the Copilot is a rule-based router** — `README.md:54` vs. no code/dependency (`grep -ri gemini` = 1 hit). `ai/copilot.py` returns f-string sentences ("I found 5 products that best match your request."); the frontend sends only the *latest* message (`services.ts:646`), so there is no conversational memory; detected intents `styling`, `seasonal_search`, `visual_search` are never routed (`copilot.py` falls through to semantic search). Starter prompts such as "Compare your two best-rated sneakers" cannot be fulfilled. *Fix:* decide Gemini's role (query understanding + grounded answer generation over retrieved products), add key management, timeouts, fallbacks and safety (Roadmap Phase 4). Do not claim Gemini until built. **P1**

**H-07 · Blocking inference inside async handlers (semantic search)** — `search.py:39-47`. `model.encode(...)` and `index.search(...)` are synchronous CPU calls inside `async def`, stalling every concurrent request on that worker. *Fix:* `run_in_threadpool`/dedicated executor or a separate inference service; cache query embeddings. **P1**

**H-08 · Fabricated metrics and claims presented as fact** — `routes/dashboard.tsx:37-52` ("Products indexed 128,410" — catalog is 105,542; "Assisted revenue $412,980"; "Conversion lift 8.7%"; static 7-day chart); `routes/login.tsx:67` ("31% lift in add-to-cart rate"); `routes/index.tsx:567-573, 751` ("Live Catalog Inventory" / "Live mock catalog" built from `mock.ts`, matchScores like `0.98`); `product.$productId.tsx:248` ("Free delivery and 30-day returns"). Consumer-protection and credibility risk for a real storefront. *Fix:* remove or replace with real aggregates from `session_events`/orders; mark demo content clearly; business policy text from config. **P1**

**H-09 · Client-trusted cart and pricing; currency mishandled** — `cart-wishlist.ts:41-100`, `cart-sheet.tsx:14-17,124`. Cart stores a full product snapshot (including `price`) in `localStorage`; totals are computed in the browser; `$`/USD is hard-coded while products can arrive in INR/EUR/GBP from budget/recommend endpoints, so totals can mix currencies. Fine for a wishlist; **unsafe as a source of truth for payment**. *Fix:* server cart holding only `(product_id, qty, variant)`; server recomputes prices at checkout. **P0 with Phase 3**

**H-10 · No observability, CI/CD, containers or production routing** — repo has no `Dockerfile`, compose, `.github/`, logging config, metrics, tracing or error reporting beyond `print()` (10 calls in runtime paths) and a Lovable-editor hook (`lovable-error-reporting.ts`). `/health` returns a constant (`main.py:90-95`) and does not check Mongo or the index. The `/api` proxy exists only in the Vite **dev** server (`vite.config.ts:11-20`); a production TanStack-Start deployment needs a real reverse proxy or `VITE_API_BASE_URL`. *Fix:* Phase 6. **P1**

**H-11 · Test suite is not a safety net** — `backend/test_*.py`. 8 files, mostly good unit tests for auth, validation and reranker scoring, but: `test_budget.py` and others call the live DB and the external FX API with no assertions; `test_intent.py`, `test_config.py`, `test_multicurrency_budget.py`, `test_exchange_rates.py` are print-scripts; no `TestClient`/HTTP-level tests; no frontend tests; no CI to run any of it. (Not executed in this audit — dependencies unavailable.) *Fix:* separate unit/integration/live, add API tests with `httpx.AsyncClient`+mongomock/`mongomock-motor`, golden relevance tests, Playwright smoke tests. **P1**

**H-12 · No image storage/CDN; third-party hot-linked images** — `database/seed.py` (Unsplash URLs), `update_product_images.py` (patching two broken Unsplash links — evidence the approach already breaks), H&M rows have no image field. Visual search depends on live remote fetches. *Fix:* object storage + CDN, immutable keys, thumbnails/WebP, upload pipeline for admin. **P1**

**H-13 · Probable startup/auth breakers needing a 5-minute check (UNVERIFIED — could not run)** — (a) `config.py:45` declares `allowed_origins: list[str]`, but `.env.example:12` and the README give a comma-separated value; pydantic-settings parses list fields as JSON, so `ALLOWED_ORIGINS=http://a,http://b` is expected to raise a settings error at import. (b) `requirements.txt` pins `passlib==1.7.4` with `bcrypt==5.0.0`; passlib 1.7.4's bcrypt back-end self-test uses a >72-byte secret which bcrypt ≥ 5 rejects, so password hashing may raise. (c) `config.py:25` default DB name `CatalogIQ` vs `.env.example:3` `catalogiq` — MongoDB database names are case-sensitive, so the two docs describe different databases. *Check:* `ALLOWED_ORIGINS=a,b python -c "import config"`; `python -c "from utils.security import hash_password as h; print(h('x'))"`. *Fix:* JSON list or a `field_validator` splitting commas; use `bcrypt` directly or pin a compatible pair; one DB name. **P0 to verify**

**H-14 · Account lifecycle and session security incomplete** — `auth.py`, `src/lib/api/auth.ts:33-44`. No email verification, password reset, password change, logout/revocation, refresh tokens or lockout; 24-hour bearer token stored in `localStorage` (readable by any XSS); signup immediately issues a token. *Fix:* HttpOnly+Secure+SameSite cookie sessions or short-lived access + rotating refresh; verification & reset flows; CSP. **P1**

### 4.3 Medium

- **M-01 · Intent detection defects** — `ai/intent_detector.py:41-135` uses raw substring tests (`word in query`): "rain" matches "training"/"brain", "wear" matches "swimwear"/"underwear", "pair" matches "repair", "best" matches "bestseller", "gym" etc. A second, different intent system (`services/intent_service.py`) has an unanchored budget regex (`:24`) that treats any number as a budget ("size 38" → "under $38"). *Fix:* word-boundary tokenisation, single intent module, test table. **P2**
- **M-02 · Duplicated taxonomy logic and oversized reranker** — category alias maps are re-declared in `recommendation_service.py` (×3), `taxonomy_service.py`, `query_parser.py`, `semantic_reranker.py` (1,313 lines); `.backup`/`.before_relevance_fix` copies are tracked. *Fix:* single taxonomy module, delete backups (history already keeps them). **P2**
- **M-03 · Recommendation engine defects** — `ai/recommendation_engine.py` defines `class RecommendationEngine` twice (`:6`, `:15`); unused `import random`; ignores `session_intent`; `/recommend` scores only the first 100 `in_stock` docs with no sort (`recommendation_service.py:45`); frontend never passes `session_id` (`services.ts:391`) so personalisation is dormant on the dashboard. **P2**
- **M-04 · Index lifecycle** — `create_hm_embeddings.py:104` `IndexFlatL2` (exact, ≈162 MB for 105,542×384 float32, loaded per worker); no versioning, no incremental updates, ID map via pickle; README claims cosine similarity while the index is `IndexFlatL2` (equivalent only if vectors are unit-length — `all-MiniLM-L6-v2` normally is, but the code never asserts it; see AI-04, unverified); legacy `create_embeddings.py` targets a non-existent `Products` collection. **P2**
- **M-05 · Non-scalable query patterns** — legacy `POST /api/search` loads up to 500 docs and scores in Python (`search_service.py:37`); `seasonal`, `stylist`, `budget` do the same; the stylist builds a full cartesian product of tops × trousers × footwear (`stylist.py:235`) — with 500 docs that can reach millions of combinations. The frontend never calls `/api/search`. **P2**
- **M-06 · FX rate fetched on every request** — `exchange_rate_service.py:13-47`, called from `recommend.py:49` and `budget_service.py:266`; no cache/TTL, no stale-rate fallback. **P2**
- **M-07 · API contract inconsistencies** — snake_case (`in_stock`, `original_price`, `page_size`) from `/products` vs camelCase (`inStock`, `originalPrice`) from `/budget`, `/stylist`, `/seasonal`; only 4 of ~20 endpoints declare `response_model`; `/products?sort=` is unvalidated; `/seasonal` returns **200** with an error message for an invalid season (`seasonal.py:146-151`). **P2**
- **M-08 · Missing input bounds** — `StylistPayload.notes` and strings unbounded (`stylist.py:12-17`); `SearchRequest.query` has no `max_length` (`semantic_search.py:21`); `IntentPayload.query`, `BudgetPayload.categories` unbounded. **P2**
- **M-09 · Accessibility/responsive gaps (source-level only)** — no `aria-live` region for the copilot conversation or search status (grep across routes/components: none); visual-search drop zone reacts to Enter but not Space and duplicates the button (`visual-search.tsx:67-102`); `onError` hides a broken image leaving a blank box (`product.$productId.tsx:144-146`); only ~26 aria/alt/role attributes in all feature code. Not validated with a screen reader or Lighthouse. **P2**
- **M-10 · Secret echo and noisy logs** — `backend/test_config.py:3-5` prints the Mongo URL and `settings.jwt_secret` at pytest collection (lands in CI logs); `tracking.ts:30-31,36` console-logs every event and the API base URL in production. **P2**
- **M-11 · Repository hygiene / destructive script** — `articles.csv` (36 MB) tracked in git; root `seed.py:37` runs `products.delete_many({})` **at import time**, hard-coded to DB `CatalogIQ`/collection `Products` and a different env var (`MONGO_URI`), no confirmation; root `routes/seasonal.py` is a divergent duplicate of `backend/routes/seasonal.py`. (`import_hm_catalog.py` does prompt before `delete_many`.) **P2**
- **M-12 · Documentation drift and public API docs** — README shows a `frontend/` tree, React Router and `docs/`, `dataset/` that do not exist; backend README endpoint table omits semantic-search/copilot/budget/stylist/seasonal/visual-search; Swagger (`/docs`, `/redoc`) enabled unconditionally (`main.py:54-55`). **P2**
- **M-13 · Upload and remote-fetch hardening** — `visual_search.py`: no `Image.MAX_IMAGE_PIXELS` policy (decompression-bomb risk within the 8 MB cap), catalog image fetches have no size limit and follow redirects; URLs come from the DB (trusted today) — treat as SSRF-sensitive once admin uploads exist. **P2**

### 4.4 Low

- **L-01** `datetime.utcnow()` deprecated (`models/user.py:10,22`, `utils/jwt.py:11`).
- **L-02** `print()` instead of structured logging (`main.py`-path: `connection.py:53,70,91`, `exchange_rate_service.py:50`, `stylist.py:195-204`, `search.py:18-29`).
- **L-03** Dead/duplicate code: repeated comment blocks in `seasonal.py:106-110` and `copilot.py:55-61`; three repeated `/** POST /semantic-search */` stubs in `services.ts:219-225`; byte-order marks in `tracking.ts` and `test_intent_event_validation.py`.
- **L-04** Login timing differs for unknown email (no bcrypt run) vs wrong password (`auth.py:70-77`).
- **L-05** `robots.txt` allows everything including `/profile`, `/dashboard`; no sitemap.
- **L-06** Google Fonts loaded from a third-party CDN (`__root.tsx:99-104`) — privacy/consent consideration.
- **L-07** Empty placeholder packages `backend/agents/`, `backend/embeddings/` while README implies functionality.
- **L-08** Brand falls back to `department` (`services.ts:116,254`), so H&M items show a department as "brand".

---

## 5. What is good and should be kept

- Auth module: bcrypt hashing, uniform login error, email normalisation, inactive-account check, 9 unit tests incl. wrong-password/inactive paths (`test_auth.py`).
- `session_events` design: weighted events, compound index, **30-day TTL index** (`session_intent_service.py:21-42`).
- `semantic_reranker` is thoughtfully structured (dedup, diversity cap, explainable `reason`), with regression tests.
- Multi-currency budget parsing and conversion math (`budget_service.py`, `exchange_rate_service.py`).
- Visual-search **upload validation** (type, size, Pillow format check, empty file) is better than most.
- `mapApiProduct` normalisation layer tolerates both catalogs' field names — a good seam for unifying data.
- Dependency supply-chain guard in `bunfig.toml` (24 h release age).
- Clean separation api/services/models in the backend; consistent shadcn/ui usage; loading skeletons exist for most lists.

---

## 6. Recommended order of work (summary)

1. **Phase 0 – Make it reproducible and honest** (C-01, C-05, C-06, H-13, H-11 core, M-10): install/start from a clean clone, fail-fast config, mocks off by default, CI running tests.
2. **Phase 1 – One catalog** (C-02, C-03, H-02, H-12): canonical collection, price/stock/image, indexes.
3. **Phase 2 – Security & accounts** (H-01, H-03, H-14, C-06 follow-up, RBAC foundation).
4. **Phase 3 – Commerce core** (C-04, H-09): server cart, orders, inventory, payments (test mode).
5. **Phase 4 – AI quality** (H-04–H-07, C-07, M-01–M-04): evaluation set, server-side filters, Gemini decision, async inference, visual index.
6. **Phase 5 – UX, a11y, admin** (H-08, M-09, admin console).
7. **Phase 6 – Production operations** (H-10, backups, monitoring, load test, launch checklist).

Full phases, tasks and acceptance criteria: [CATALOGIQ_IMPLEMENTATION_ROADMAP.md](CATALOGIQ_IMPLEMENTATION_ROADMAP.md).
