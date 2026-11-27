# CatalogIQ AI — Backend & API Review

Commit audited: `5d7ba72`. Companion to [CATALOGIQ_AUDIT.md](CATALOGIQ_AUDIT.md) (IDs `C-/H-/M-/L-`). **Static review — the API was not started and no tests were executed** (dependencies not installable offline). Items that need runtime confirmation are marked *verify*.

---

## 1. Summary

The existing API is a clean, readable FastAPI codebase (api → services → models) with solid input validation on the authentication and visual-search paths. It is, however, a **read-mostly discovery API**: there is no cart, checkout, order, payment, inventory, role or admin surface (C-04), almost every endpoint is anonymous and unthrottled (H-01, H-03), data comes from two different collections depending on the endpoint (C-02), and there is no logging, monitoring or HTTP-level test coverage (H-10, H-11).

---

## 2. Endpoint-by-endpoint review

Auth column: **public** = no token required. "Bounds" = request-size/field limits.

### 2.1 Authentication — `api/v1/auth.py`

| Endpoint | Behaviour | Strengths | Issues |
|---|---|---|---|
| `POST /auth/signup` | Normalises email, bcrypt-hashes, inserts into `users`, returns `{access_token}` | Pydantic `EmailStr`, password 8–128, `full_name` ≤100; 409 on duplicate | No unique index so the `DuplicateKeyError` branch is dead and concurrent signups can duplicate (H-02); token issued with no email verification (H-14); no password-strength policy beyond length; bcrypt truncates at 72 bytes while `max_length=128` accepts longer strings *(verify bcrypt version behaviour, H-13)* |
| `POST /auth/login` | Verifies hash, checks `is_active`, returns token | Uniform 401 message; 403 for inactive | No lockout / rate limit (H-01); unknown email skips hashing → timing difference (L-04); no audit log |
| `GET /auth/me` | Returns profile from token `sub` | Handles ObjectId and string ids | **Does not check `is_active`** — a deactivated user with a still-valid token keeps access until expiry (24 h) |
| `PUT /auth/profile` | Updates `full_name/preferred_size/style_keywords` | Max-length validation; only whitelisted fields | Same `is_active` gap; no optimistic concurrency; `preferred_size` is free text |

Missing: logout/revocation, refresh, change/reset password, email verification, delete-account/export (privacy), role/permission claims.

### 2.2 JWT & authorization — `utils/jwt.py`, `dependencies.py`

- HS256, 24 h (`config.py:37`), claims `sub`, `email`, `exp` only. No `iat`, `jti`, `aud/iss`, `role`, `token_version`.
- Default secret `change-me-secret` and no fail-fast (C-06).
- `get_current_user` (optional) / `get_required_user` are the only guards and are used **only** by the two profile endpoints. There is no role dependency (`require_role("admin")`) and no ownership checks, because no user-owned resources exist yet.
- Uses `datetime.utcnow()` (deprecated, L-01).

### 2.3 Product APIs

| Endpoint | Source | Issues |
|---|---|---|
| `GET /products` | `products` | `sort` accepts any string and silently falls back to `name`; `category` is exact, case-sensitive (`product_service.py:41`); `count_documents` + `skip/limit` on every call; no indexes (H-02); response uses snake_case (`in_stock`, `page_size`) while other endpoints use camelCase (M-07); no text/brand/colour/size/stock filters; deep `skip` pagination will degrade on 105k rows |
| `GET /products/{id}` | `products` by `_id` | Cannot resolve H&M `article_id`s (C-02); mutates the loaded dict in `_to_product` (`doc.pop("_id")`) — harmless but fragile; returns 404 correctly |
| *(missing)* | | `POST/PUT/DELETE /admin/products`, bulk import, variants, facets, `GET /categories` |

### 2.4 Search & discovery APIs

| Endpoint | Behaviour | Issues |
|---|---|---|
| `POST /semantic-search` | Intent → (recommendation branch \| FAISS top-100 → rerank → top_k) | `top_k` default 10, max 50; **no `page`, filters, sort** (H-04); `query` has `min_length=1` but no `max_length` (M-08); `session_id` unbounded/unvalidated; sync `encode`/`search` on the event loop (H-07); response key `products[].product` is H&M-shaped with no price/image (C-03); two different response shapes depending on branch (`retrieved_candidates` only in one) |
| `POST /search` (legacy) | Keyword scoring over ≤500 docs | Not used by the frontend; loads documents into memory and sorts in Python (M-05); `interpretation` string is canned; keep or remove deliberately |
| `GET /recommend` | Currency-aware, session-aware scoring over first 100 in-stock `products` | Good currency validation (400) and FX error → 503; but unsorted first-100 sample, `session_id` never sent by the frontend (M-03); redundant condition `max_price is not None or currency != "USD"` (`recommend.py:45-47`); converts prices by mutating results |
| `POST /intent` | Rule classifier | Unanchored budget regex (M-01); unbounded query |
| `POST /intent/event` | Writes behaviour events | **Anonymous; accepts `purchase`; client-chosen `session_id`** (H-03); no per-session rate cap (event flood → unbounded `session_events` growth until TTL) |
| `GET /seasonal` | Keyword season rules over ≤500 docs | Invalid season returns **200** with a message instead of 422/400 (`seasonal.py:146-151`); duplicated comment blocks; root-level `routes/seasonal.py` is a diverged copy (M-11) |
| `POST /stylist` | Greedy/combinatorial outfit builder | `notes`/strings unbounded (M-08); `budget` has no upper bound; **cartesian product** of top × trousers × footwear (`stylist.py:235`) can explode; debug `print` of request and products (`:195-204`); USD assumed |
| `POST /budget` | Greedy allocator | Good: priority whitelist, de-dup of categories, `$in` of anchored case-insensitive regexes. Issues: `categories` list unbounded; regex match prevents index use (M-05); `budget` has no max; USD assumed; ≤500 docs |
| `POST /visual-search` | CLIP similarity over first 100 products | **Strong upload validation** (415/413/400); but per-request remote fetch + CLIP on the event loop (C-07); no auth/rate limit; no pixel cap (M-13) |
| `POST /copilot/chat` | Rule router → templated reply | `message` ≤2000 and trimmed (good); stateless; mixes two data sources; no Gemini (H-06); `session_id` ≤128 |

### 2.5 Cart, checkout, orders, payments, inventory — **do not exist**

Nothing to review; see §4 for the proposed surface. The only related server artefact is the `cart`/`purchase` *event type* in `session_events`.

---

## 3. Cross-cutting backend review

### 3.1 Database indexing and validation
- Only `session_events` gets indexes at startup (`main.py:40` → `_ensure_indexes`). `users` has **no unique email index**; `products` has none; `catalog_products` gets indexes only if the import script ran. (H-02)
- No MongoDB JSON-schema validators; Pydantic models exist for `products` and `users`, none for `catalog_products` or `session_events`.
- `ProductInDB` and `Product` require `image: str`, `rating: float`, `reviews: int`, `description: str` — H&M documents (no image/rating/reviews) would fail `Product(**doc)` if routed through `ProductService`, another reason the two catalogs cannot simply be merged by pointing endpoints at one collection.
- `database/connection.py` reconstructs the client lazily inside `get_database()` and uses a private attribute (`_client.delegate._closed`) — works but is a workaround for dev reloads; two code paths create clients with duplicated options.
- Connection timeouts are set (10 s) — good.

### 3.2 Error handling and logging
- No global exception handlers, no error envelope, no request/correlation ID. Mongo/FX/FAISS exceptions surface as generic 500s.
- No logging configuration; diagnostics are `print()` (L-02). Nothing is emitted that an operator could alert on. The root `/health` returns a constant and does not check DB, model or index (H-10).
- FX failure is handled well (`RuntimeError` → 503) in `/recommend`; in the copilot it becomes a user-facing message.

### 3.3 Rate limiting and security
No rate limiting, request-size limit (other than visual-search), security headers, CSRF considerations for cookie auth (n/a today, token in header), or abuse detection. CORS allows `*` methods/headers with credentials for an origin allow-list that defaults to localhost only (`config.py:45-54`) — correct posture, but production origins must be supplied via an env var whose documented format likely breaks parsing (H-13a). Details in [CATALOGIQ_SECURITY_REVIEW.md](CATALOGIQ_SECURITY_REVIEW.md).

### 3.4 API documentation
- Swagger/ReDoc are auto-generated and always on (`main.py:54-55`).
- Only 4 of ~20 operations declare `response_model`, so generated schemas for products/search/copilot are empty objects; handlers return raw dicts.
- `backend/README.md` endpoint table lists 8 endpoints and describes `/api/search` as the main search; it omits semantic-search, copilot, budget, stylist, seasonal and visual-search (M-12).
- URLs are `/api/...` while code is organised as `api/v1`; there is no `/v1` in the path, so a breaking change has no versioning escape hatch.

### 3.5 Automated tests
Present: `test_auth.py` (9 async tests with mocked Motor — good), `test_copilot_validation.py`, `test_intent_event_validation.py`, `test_recommendation_filtering.py`, `test_semantic_reranker_relevance.py`, `pytest.ini` (`asyncio_mode=auto`).
Absent/weak: HTTP-level tests (no `TestClient`/`AsyncClient`), contract tests against the frontend `types.ts`, DB integration tests, load tests; `test_budget.py` and others hit the live database and FX API without assertions; `test_config.py` prints the JWT secret and Mongo URL (M-10); no coverage reporting; no CI (H-11). *Tests were not run in this audit.*

---

## 4. Proposed API surface (proposal — additive; names are suggestions)

Conventions to adopt first: `/api/v1` prefix; one error envelope `{error:{code,message,request_id,details?}}`; snake_case on the wire (client maps once in `mapApiProduct`); `response_model` on every route; cursor or page/size pagination with `total`; idempotency keys on every money-moving POST; request IDs in logs and responses.

| Area | Endpoints | Notes |
|---|---|---|
| Auth/account | `POST /auth/logout`, `/auth/refresh`, `/auth/verify-email`, `/auth/forgot-password`, `/auth/reset-password`, `POST /auth/change-password`, `GET/POST/PUT/DELETE /me/addresses`, `DELETE /me` | Roles: `customer`, `admin`, optionally `staff`; `require_role` dependency |
| Catalog | `GET /products` (facets, q, brand, colour, size, in_stock, price range), `GET /products/{id}`, `GET /categories`, `GET /products/{id}/related` | Reads canonical collection (Architecture §6) |
| Cart | `GET /cart`, `POST /cart/items`, `PATCH /cart/items/{id}`, `DELETE /cart/items/{id}`, `POST /cart/merge` | Stores `(product_id, variant, qty)` only; prices computed server-side |
| Checkout | `POST /checkout/quote`, `POST /checkout/start` (reserves stock), `POST /checkout/confirm` | Re-validates price, stock, currency, shipping, tax |
| Payments | `POST /payments/intent` (test-mode keys only), `POST /webhooks/payment` | Signature verification, idempotent event handling, no card data touches the API |
| Orders | `GET /orders`, `GET /orders/{id}`, `POST /orders/{id}/cancel`, `POST /orders/{id}/return` | Ownership enforced; state machine in Architecture §7 |
| Admin | `GET/POST/PUT/PATCH /admin/products`, `POST /admin/products/import`, `POST /admin/uploads/sign`, `GET /admin/orders`, `PATCH /admin/orders/{id}`, `PATCH /admin/inventory/{sku}`, `GET /admin/users`, `GET /admin/metrics` | Admin role + audit log |
| AI | existing endpoints, plus server-side `page/filters/sort` on `/semantic-search`; `GET /ai/health`; copilot gets `conversation_id` | Keep current request shapes backward-compatible |
| Ops | `GET /health/live`, `GET /health/ready` (Mongo + model + index), `GET /metrics` (internal) | |

---

## 5. Prioritised backend fixes

| Pri | Fix | Finding |
|---|---|---|
| P0 | Reproducible `requirements.txt`; startup lifecycle for model/index; one config format | C-01, H-13 |
| P0 | Fail-fast secrets; `is_active` check on token use; add role claim scaffolding | C-06 |
| P0 | Index bootstrap (unique `users.email`, product indexes) | H-02 |
| P0 | Canonical catalog and endpoint rewiring | C-02, C-03 |
| P1 | Rate limiting, auth on events, request/size bounds | H-01, H-03, M-08 |
| P1 | Logging/metrics/health-ready, error envelope, request IDs | H-10 |
| P1 | HTTP-level tests + CI | H-11 |
| P1 | Server-side search filters/pagination | H-04 |
| P2 | Response models, `/v1` versioning, camel/snake consistency, 4xx for invalid season | M-07 |
| P2 | FX cache; remove or scale legacy keyword search and 500-doc loaders | M-05, M-06 |

**Preserve:** auth module and tests, session-event service, budget/FX math, upload validation, services/api layering.
