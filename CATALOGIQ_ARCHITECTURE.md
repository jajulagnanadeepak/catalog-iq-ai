# CatalogIQ AI — Architecture (As-Is and Target)

Commit audited: `5d7ba72`. Companion to [CATALOGIQ_AUDIT.md](CATALOGIQ_AUDIT.md). Finding IDs (C-xx, H-xx …) refer to that register.

Everything in §1–§4 describes **what the code does today**. §5 onward is a **proposal** that preserves MongoDB, FAISS and the existing search pipeline.

---

## 1. System context (as-is)

```
 Browser (TanStack Start SPA/SSR)
   │  Axios  baseURL "/api"  (dev: Vite proxy → 127.0.0.1:8000; prod: NOT configured, H-10)
   │  localStorage: catalogiq.token, catalogiq.session_id, cart v1, wishlist v1
   ▼
 FastAPI app (backend/main.py)  — single process, no auth middleware, no rate limit
   ├─ api/v1/*      products · search(legacy keyword) · intent · recommend · auth · budget
   ├─ routes/*      semantic_search · copilot · stylist · seasonal · visual_search
   ├─ services/*    product · search · recommendation · budget · exchange_rate ·
   │                semantic_reranker · session_intent · taxonomy · query_parser · intent
   └─ ai/*          copilot · intent_detector · recommendation_engine
        │                         │                         │
        ▼                         ▼                         ▼
  MongoDB Atlas            In-process models          External HTTP
   users                    MiniLM-L6-v2 (384-d)       api.frankfurter.dev (FX)
   products (12 demo)       FAISS IndexFlatL2          catalog image URLs (visual search)
   catalog_products (H&M)   CLIP ViT-B/32 (torch)
   session_events (TTL 30d)
   (Products — legacy, root seed.py)
```

Not present anywhere: Gemini, object storage/CDN, payment gateway, email service, cache (Redis), queue/worker, admin console, logging/metrics stack, container or CI configuration.

---

## 2. Backend inventory

### 2.1 Endpoints (all under `/api` except `/health`)

| Method & path | Router file | Auth | Data source | Used by frontend |
|---|---|---|---|---|
| `GET /health` | `main.py:90` | none | constant (no DB/index check) | no |
| `GET /products` | `api/v1/products.py` | none | `products` | yes (`getProducts`) |
| `GET /products/{id}` | `api/v1/products.py` | none | `products` by `_id` | yes (`getProduct`) |
| `POST /search` | `api/v1/search.py` | none | `products` (≤500 docs, keyword) | **no** |
| `GET /recommend` | `api/v1/recommend.py` | none | `products` (first 100 in-stock) + FX | yes (limit only) |
| `POST /intent` | `api/v1/intent.py` | none | rules | yes (`postIntent`) |
| `POST /intent/event` | `api/v1/intent.py` | **none** | writes `session_events` | yes (`tracking.ts`) |
| `POST /auth/signup` · `/login` | `api/v1/auth.py` | none | `users` | yes |
| `GET /auth/me` · `PUT /auth/profile` | `api/v1/auth.py` | JWT | `users` | yes |
| `POST /budget` | `api/v1/budget_optimizer.py` | none | `products` (≤500) | yes |
| `POST /stylist` | `routes/stylist.py` | none | `products` (≤500) | yes |
| `GET /seasonal` | `routes/seasonal.py` | none | `products` (≤500) | yes |
| `POST /visual-search` | `routes/visual_search.py` | none | `products` (first 100) + remote images + CLIP | yes |
| `POST /semantic-search` | `routes/semantic_search.py` | none | FAISS → `catalog_products` | yes (`postSearch`) |
| `POST /copilot/chat` | `routes/copilot.py` | none | mixes `products` (budget) and `catalog_products` (semantic) | yes |

### 2.2 MongoDB collections (inferred from code; Atlas not inspected)

| Collection | Written by | Documents | Key fields (from code) | Indexes created by code |
|---|---|---|---|---|
| `users` | `auth.py` signup/profile | unknown | `email`, `full_name`, `hashed_password`, `created_at`, `is_active`, `preferred_size`, `style_keywords` | **none** (H-02) |
| `products` | `database/seed.py` | 12 | `_id` (`p-001…`), `name, brand, category, price, original_price, rating, reviews, image, colors, sizes, tags, description, in_stock, currency` | none |
| `catalog_products` | `database/import_hm_catalog.py` | 105,542 (per `articles.csv`; **not verified in Atlas**) | `_id=article_id, article_id, name, product_type, category, department, section, garment_group, colour, description` — **no price/image/stock/rating** (C-03) | `article_id` (unique), `name`, `category`, `department`, `colour` |
| `session_events` | `session_intent_service.py` | unknown | `session_id, event_type, score, category, product_id, created_at` | `session_id`, `(session_id, created_at)`, TTL 30 days |
| `Products` (capital P) | root `seed.py` (`delete_many` then insert) | unknown | `product_id` etc. | `product_id` unique + 4 others |

`ProductInDB`/`Product` Pydantic models describe the `products` shape only; there is **no model for `catalog_products`**.

### 2.3 Search / AI data flow (semantic search)

```
POST /semantic-search {query, top_k(10), session_id?}
  1  IntentDetector.detect_intent(query)                 ai/intent_detector.py  (rules)
  2  session_intent_service.get_session_intent(sid)      Mongo aggregate over session_events
  3a intent == "recommendation" → RecommendationEngine.recommend → semantic_search(query, 20) → dedupe by name
  3b else:
        semantic_search(query, top_k=100)                search.py
           SentenceTransformer.encode (sync)  →  FAISS IndexFlatL2.search  →  Mongo $in on catalog_products
        SemanticReranker.rerank(...)                     hard category filter (post-retrieval),
           score = .40 semantic + .15 keyword + .35 attributes + .10 intent + .10 occasion + .15 query-match   (Σ = 1.25)
           → dedupe(name, product_type) → diversity cap (0.35/category) unless category named → reason string
  4  JSON {intent, session_intent, count, products[ {rank, article_id, score, …, reason, product{…}} ]}
```

Copilot (`ai/copilot.py`): rule router → `budget_search` → `BudgetService` (products + FX); `recommendation` → engine; everything else (incl. detected `styling`, `seasonal_search`, `visual_search`) → the semantic path above. Responses are templated strings; no LLM call.

---

## 3. Frontend inventory

TanStack Start (file routes in `src/routes`, generated `routeTree.gen.ts`), React Query for fetching, a root `AuthProvider`, theme provider, Sonner toasts.

| Route | File | Data | Auth gate | Notes |
|---|---|---|---|---|
| `/` | `index.tsx` (36 KB) | **hard-coded `PRODUCTS` mock** | none | "Live catalog" is mock (H-08) |
| `/search` | `search.tsx` | `/semantic-search` | none | pagination/filter client-side (H-04) |
| `/product/$productId` | `product.$productId.tsx` | `/products/:id` (+fallback) | none | wrong-product fallback (C-02/C-05) |
| `/dashboard` | `dashboard.tsx` | static numbers + `/recommend` + `/products` | none | fabricated stats (H-08) |
| `/copilot` | `copilot.tsx` | `/copilot/chat` | none | stateless (H-06) |
| `/stylist` · `/budget` · `/seasonal` · `/visual-search` | respective files | respective endpoints | none | all fall back to mock on error |
| `/login` · `/signup` | | `/auth/*` | none | |
| `/profile` | `profile.tsx` | `/auth/me`, `PUT /auth/profile` | in-component only | no route guard |
| *(absent)* | | | | `/checkout`, `/orders`, `/admin`, `/wishlist` page, `/cart` page |

State: cart and wishlist in `localStorage` (`cart-wishlist.ts`, synced via a custom event); token in `localStorage`; anonymous `session_id` = random UUID in `localStorage` (`tracking.ts`). Server rendering is enabled (`server.ts`, `start.ts` add an error page and CSRF middleware for server functions), but **no server functions are used** — all data goes through client-side Axios to the Python API.

---

## 4. Architecture assessment

| # | Observation | Impact | Finding |
|---|---|---|---|
| A1 | Two product datasets with different schemas and IDs, consumed by different endpoints | Search ≠ catalog ≠ cart | C-02, C-03 |
| A2 | Model/index loaded at **import time**; heavy native libs imported from several modules | Cold start, test fragility, cannot start without artefacts | C-01 |
| A3 | Stateless, but state is in-process (model, FAISS, `lru_cache` CLIP) | Each worker holds ≈162 MB index + models; scaling = copying memory | M-04 |
| A4 | CPU-bound inference runs on the async event loop | One slow request stalls the worker | C-07, H-07 |
| A5 | Frontend masks API failures with mock data | Outages invisible to users and operators | C-05 |
| A6 | Trust boundary is the browser (cart price, session id, event type) | Not safe for payments or analytics | H-03, H-09 |
| A7 | No separation of public / authenticated / admin API surfaces | Cannot add checkout or admin safely | C-04 |
| A8 | No config for prod routing (`/api` proxy is dev-only), CORS localhost-only default | Frontend cannot reach API after deploy | H-10 |
| A9 | Observability absent | Cannot operate or debug a live system | H-10 |

The *shape* of the codebase (api → services → models; AI separated from CRUD) is fine to grow from. The problems are data unification, trust boundaries, and operations — not a need to re-architect.

---

## 5. Target architecture (proposal — additive, no rewrite)

```
 Browser ──HTTPS──► CDN/Edge (static, images, WAF, rate limit)
                      │
              ┌───────┴────────────┐
              ▼                    ▼
      Web (TanStack Start)     API gateway / reverse proxy  (/api/* → FastAPI)
                                   │
                    ┌──────────────┼───────────────────────────────┐
                    ▼              ▼                               ▼
              FastAPI "core"   FastAPI "ai"  (or same app, separate router set)
              auth · catalog   semantic-search · copilot · stylist ·
              cart · orders    visual-search · recommend
              payments(webhook)   │ inference pool (threadpool/worker)
              admin · inventory   │ FAISS text index  +  FAISS image index (new)
                    │             │ Gemini client (timeouts, fallback, cache)
                    ▼             ▼
              MongoDB Atlas  (users, products*, catalog_products, orders,
                              carts, inventory, payments, session_events, audit_log)
              Object storage + CDN (product images)
              Redis (optional): rate limits, FX cache, query-embedding cache
              Observability: structured logs, metrics, traces, error tracking
```

\* `products` becomes the **canonical sellable catalog** (§6). `catalog_products` is retained untouched as the immutable source of truth for the H&M text data and for index builds.

### 6. Canonical catalog (resolves C-02 / C-03)

Proposal (field names are suggestions, to be confirmed by you — nothing here exists in the repo yet):

- Keep `catalog_products` as-is (read-only source). Create a **new** collection (e.g. `catalog_items`) keyed by `article_id` that adds `sku`, `price`, `currency`, `image` (CDN key), `in_stock`, `stock_qty`, `rating`/`review_count` (only if a real source exists), `status` (draft/active/archived), `created_at/updated_at`.
- The 12 demo products are migrated into the same collection tagged `source: "demo"` and hidden in production.
- FAISS ID map already uses `article_id`; semantic results then resolve against `catalog_items` by the same key, so `/products/{article_id}` works for every search result.
- All endpoints read the one collection; the legacy `search.py` keyword endpoint can be removed or pointed at it.
- Changes are additive; no `delete_many`, no in-place mutation of `catalog_products`; every migration script is idempotent, dry-run-first, and checkpointed.

### 7. Order lifecycle (target, for Phase 3)

`cart (open)` → `checkout_started` (prices & stock re-validated server-side, stock **reserved** with TTL) → `payment_pending` (gateway intent created, **test mode only**) → `paid` (webhook, idempotent) → `fulfilling` → `shipped` → `delivered`; side branches `cancelled`, `payment_failed`, `refunded`, `returned`. Inventory is decremented on `paid` via atomic `findOneAndUpdate` with `stock_qty >= qty`; reservations expire via TTL index. All transitions are written to an append-only `order_events` collection.

### 8. Deployment topology (target)

- **Web:** deploy the TanStack Start build to a Node/edge host (the repo is Lovable-managed; confirm the intended target — `server.ts` is written for a fetch-style runtime such as Cloudflare Workers/Nitro).
- **API:** container (Gunicorn/Uvicorn workers) with models baked into the image or fetched from object storage at start; readiness probe waits for model + index + Mongo.
- **Config:** 12-factor env vars, secrets in the platform secret manager; separate dev/staging/prod Atlas projects.
- **Index artefacts:** versioned (`text-index-v{n}`, `image-index-v{n}`) in object storage with a manifest; deploy picks the manifest version; rollback = previous manifest.
- **Data safety:** Atlas continuous backup + point-in-time restore tested quarterly; staging seeded from anonymised data only.

---

## 9. Decisions needed from you (do not guess)

1. **Source of price, stock and images** for the 105,542 H&M articles (supplier feed vs. clearly-labelled synthetic demo data). This is a business/legal choice.
2. **Intended web hosting target** (Lovable-hosted, Cloudflare, Vercel, self-hosted Node).
3. **Payment gateway and market** (e.g. Razorpay or Stripe; currencies INR/USD/EUR/GBP are already supported by the budget code).
4. **Gemini's role**: query understanding only, grounded answer generation, or both.
5. **Is checkout in scope for the first public release**, or a catalogue-with-wishlist launch first?
