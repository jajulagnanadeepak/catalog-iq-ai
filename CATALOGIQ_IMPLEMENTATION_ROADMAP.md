# CatalogIQ AI — Final Prioritised Implementation Roadmap (v2)

**Status:** For approval. Nothing is implemented. Per your instruction, no code is written until you approve **Phase 1**.
**Baseline:** commit `5d7ba72` (`main`). The findings come from [CATALOGIQ_AUDIT.md](CATALOGIQ_AUDIT.md) (IDs `C-/H-/M-/L-`), [Security](CATALOGIQ_SECURITY_REVIEW.md) (`SEC-`), [AI](CATALOGIQ_AI_REVIEW.md) (`AI-`) and [UI/UX](CATALOGIQ_UI_UX_REVIEW.md) (`UX-`).
**Supersedes:** roadmap v1, which used a 0–6 phase plan. This version follows your five-phase order from the transformation brief. I changed the order only where a technical dependency required it (§4).

---

## 1. Findings that shape everything else

Before planning, I analysed `articles.csv` (read-only) against the brief. Four facts decide the scope. Each of them needs a decision from you (§3).

### 1.1 The catalogue is fashion-only

| Fact (from `articles.csv`) | Value |
|---|---|
| Articles | **105,542**, no duplicate `article_id` (the import already enforces this, `import_hm_catalog.py:27-28, 92-93`) |
| Distinct `product_code` | **47,224**. Each product code groups colour variants of one style, which gives a natural *product → variant* model |
| Product groups | 19. The main ones are upper body 42,741, lower body 19,812, full body 13,292, accessories 11,158, underwear 5,490, **shoes 5,283** and swimwear 3,127 |
| Product types | 131 (for example: trousers 11,169, dress 10,362, sweater 9,302, sneakers 1,621, boots 1,028) |
| Audience (`index_group_name`) | Ladieswear 39,737; **Baby/Children 34,711 (32.9 %)**; Divided 15,149; Menswear 12,553; Sport 3,392 |
| Empty `detail_desc` | 416 |
| Price, stock, size, image, rating, brand | **none in the data** |

**What this means for the example queries in the brief**

| Example query | Can this catalogue serve it? |
|---|---|
| "Black formal shoes for office" | Yes, but the word "formal" appears only once in the text. It depends on query understanding that maps *formal/office* onto types such as pumps, flat shoes and oxford-style shoes, and on the eval set. |
| "Running shoes under ₹3,000 for beginners" | Partly. There are 1,621 sneakers and 382 items mention "running". "Under ₹3,000" **needs a price**, and there isn't one. |
| "Show me products suitable for a college student" | Yes, as a fashion query (budget and casual style intent). |
| "Products similar to this one" | Yes. FAISS neighbours give this directly. |
| "A laptop for programming and machine learning" | **No.** The 39 "laptop" hits are laptop *bags* and accessories. |
| "Best headphones for travelling" | **No.** The 16 hits are accessories. |

The pipeline itself is not tied to fashion. Serving electronics needs **a different product data source** and category-specific attributes. Until that exists, the system should say *"we don't carry laptops"* rather than return laptop bags. That honest behaviour is part of Phase 3.

### 1.2 Data rights and real goods

- **Real customers need real merchandise.** That means a price you will honour, stock you hold, images you may use, and a fulfilment path. The H&M dataset describes H&M's products, not yours. Selling against it would mean taking orders for goods you cannot ship.
- **Licence.** As far as I know, this dataset was published for the Kaggle "H&M Personalized Fashion Recommendations" competition under competition-only, non-commercial terms. I have not verified this here, so please check the terms or ask counsel before any public or commercial use. "H&M" is also a trademark.
- **Consequence.** The 105,542-item catalogue stays preserved and fully usable as **development and demo data**, clearly labelled, and as a benchmark for search quality. Production goods come from your own feed, and the canonical model in Phase 1 is designed to take both.

### 1.3 What this session can and cannot do

| Limitation | Effect | How to fix it |
|---|---|---|
| Network is off: `pip`/`npm` are refused, and FastAPI, Motor, FAISS, sentence-transformers, torch and others are **not installed** in this workspace | I can write code and tests, but I **cannot run** the backend, its tests or the frontend build here | Allow package installs in your network settings and start a new chat (the current chat may not pick it up), or run the test commands I give you and paste the output |
| The repo is attached **read-only** | I cannot create branches or push | Grant push access to `jajulagnanadeepak/catalog-iq-ai`. I will then work on feature branches and open PRs, and never push to `main` directly |
| No Atlas access | No data analysis of the live DB; no migration runs | You run the dry-run migration and share the report, or you give me a **staging** cluster (never production) |

Your acceptance rule is that a feature is complete only once it is tested and verified. Under the limits above, I will mark a task "code complete, awaiting verification" until the tests have actually been run. I won't report it as done before then.

---

## 2. Gap analysis: the brief against the current code

Status key: ✅ works · 🟡 partial or mock · ❌ missing.

| Brief section | Requirement | Today | Phase |
|---|---|---|---|
| §2 Customer | Register, login, profile | ✅ basic (no verification, reset or revocation) | 1 |
| | Addresses | ❌ | 2 |
| | Browse, search, filter, sort | 🟡 filtering and sorting happen client-side over one page; mock fallback | 1 (honesty) → 2 → 3 |
| | Details, gallery, variants, price, availability | 🟡 12 demo products only; H&M has no price, image or stock | 1–2 |
| | Ratings and reviews | 🟡 static demo values; no reviews | 2 (reviews), 4 (moderation) |
| | Wishlist, cart, persistence, quantity | 🟡 `localStorage` only | 2 |
| | Coupons, shipping, checkout, payment, orders, tracking, cancellation, returns, refunds, notifications | ❌ | 2 |
| §2 Product management | Categories, brands, variants, pricing, discounts, stock, images, attributes | ❌ (two disconnected collections) | 1–2, 4 |
| §3 Discovery | Semantic search | ✅ FAISS, exact L2 | keep; 3 |
| | Keyword and hybrid search | 🟡 keyword scoring only inside the rerank; no lexical retrieval | 3 |
| | Query understanding and constraints | 🟡 rule-based parser with known bugs (AI-08) | 3 |
| | Server-side filters, pagination | ❌ (H-04) | 3 (with a minimal form in 2) |
| | Metrics | ❌ no eval set (AI-09) | **baseline in 1**, gate in 3 |
| §4 Copilot | Tool-grounded, clarifying, multi-turn, no hallucination | 🟡 rule-based, single turn | 3 |
| §5 Stylist | Real products, occasion, colour, budget | 🟡 runs on 500 docs | 3 |
| §6 Budget | Real prices | 🟡 demo prices; H&M has none | 3 (after prices exist) |
| §7 Visual search | Upload → similar catalogue items | 🟡 fetches up to 100 remote images on every request (C-07) | 3 |
| §8 Recommendations | Content, session, popularity, co-purchase | 🟡 content and session pieces exist; nothing is measured | 3 (co-purchase only once orders exist) |
| §9 Admin | Full console and backend RBAC | ❌ (C-04) | RBAC core in 1; console in 4 |
| §10 Security | All items | 🟡 see the Security review | 1 (critical), 5 (hardening) |
| §11 Data integrity | Indexes, validation, transactions, migrations | ❌ (H-02) | 1–2 |
| §12 UI/UX | Premium, accessible, complete states | 🟡 good component base; misleading content | 1 (honesty), 2 and 4 (flows), 5 (polish and a11y) |
| §13 Testing | Unit, API, E2E | 🟡 a few unit tests; scripts that only print | from Phase 1, every phase |
| §14 Deployment | Full production infrastructure | ❌ (H-10) | CI in 1; staging in 2; production in 5 |
| §15 AI reliability | Provider abstraction, fallbacks, cost | ❌ (there is no external LLM today) | 3 |

---

## 3. Decisions and approvals needed

| # | Decision | Recommendation | Blocks |
|---|---|---|---|
| **D1** | **Where production products come from.** Options: (a) your own supplier or ERP feed; (b) keep the H&M data as labelled demo data only; (c) both | **(c).** Build the schema for real goods, keep H&M as `source:"hm_demo"`, hidden in production | Phase 2 checkout scope |
| **D1b** | Demo pricing and stock for staging | Generate **clearly labelled synthetic** prices and stock for staging only (`is_synthetic: true`). This makes the "₹3,000" style flows testable. They are never shown in production. | Phase 2 testing |
| **D2** | Electronics and other categories (the laptop and headphones examples) | Out of scope until a data source exists. The schema supports category attributes now. | Phase 3 eval set |
| **D3** | Payment gateway (**sandbox or test mode only** during development) | **Razorpay** for an INR-first market (UPI and cards), behind a gateway interface so Stripe can be added later | Phase 2 |
| **D4** | LLM for the copilot and query understanding | **Gemini** (as you described), behind a provider interface with a deterministic fallback, so the app works with no LLM at all | Phase 3 |
| **D5** | Hosting (cost-effective; see §9) | Frontend on a managed edge or static host; API as one container (≥2 GB RAM); Atlas; object storage and CDN | Phase 2 staging |
| **D6** | Release scope for v1.0 | Catalogue, search, cart, sandbox checkout, orders, admin. Leave returns, refunds and reviews for v1.1 if time is tight. | Phase ordering |
| **D7** | Package manager and Python version | `bun` (lockfile, `bunfig` guard already present); Python 3.11 | Phase 1 |
| **A1** | **Grant push access** (feature branches and PRs only) | Required to deliver Phase 1 as reviewable PRs | Phase 1 |
| **A2** | **Allow package installs** (network) | Required for me to run tests myself | Phase 1 verification |
| **A3** | Approve the Phase 1 data operations: additive only, dry-run first (§5.3) | Required before any script touches Atlas | Phase 1 WS-C |

The only Phase 1 decisions I strictly need are **A1, A2 and D7**, plus a yes or no on the **D1 direction**. Everything else can be settled during Phase 1.

---

## 4. Phase order and why it differs slightly from yours

I kept your order: **1 Foundation → 2 Core commerce → 3 AI → 4 Admin → 5 Quality and production.** There are four adjustments, each driven by a dependency:

1. **CI and tests start in Phase 1**, not Phase 5. Your Definition of Done needs every feature tested, so the harness must exist first. Phase 5 broadens it into load, E2E-at-scale and penetration testing.
2. **The search evaluation baseline is set in Phase 1.** Phase 2 already changes the catalogue and product resolution, and §3 of the brief requires measured improvement, which needs a "before" number.
3. **The RBAC core (roles plus `require_role`) is in Phase 1.** Phase 2 adds stock and order endpoints that need staff and admin protection from day one. The admin *console* stays in Phase 4.
4. **Minimal admin inventory and order APIs are in Phase 2.** Without them, checkout cannot be tested end to end (nobody can stock items or mark orders shipped). Phase 4 builds the full UI and analytics on top.

```
Phase 1 Foundation ─► Phase 2 Core commerce ─► Phase 4 Admin ─► Phase 5 Production ─► v1.0
        │                     │                      ▲
        └──► (eval baseline) ─┴─► Phase 3 AI ────────┘   (Phase 3 can overlap Phase 2's second half)
```

Estimates are rough, assume one engineer working with me, and will be re-estimated at the end of Phase 1.

| Phase | Effort | Exit gate |
|---|---|---|
| 1 Foundation | 2–3 weeks | Reproducible, honest, secure-by-default, one catalogue, CI green, eval baseline |
| 2 Core commerce | 4–5 weeks | Register → … → order history E2E passes with the sandbox gateway |
| 3 AI | 3–4 weeks | Eval metrics ≥ baseline; copilot passes the grounding tests; visual search runs without remote fetching |
| 4 Admin | 2–3 weeks | Admin E2E passes; all business metrics come from real queries |
| 5 Production | 2–3 weeks | Production deployed; restore drill done; load test passes; security gate passes |

---

## 5. Phase 1 — Critical Foundation (detailed; this is what I'm asking you to approve)

**Objective.** Make the existing application reproducible, honest, secure by default, and backed by one canonical catalogue, without losing any working feature or any of the 105,542 items.

**Out of scope for Phase 1.** Cart, checkout, payments, new AI features, the admin UI and visual redesign.

### 5.1 Workstreams, files and approach

Each workstream is one branch and one PR, with small logical commits and no history rewrites. The `AGENTS.md` Lovable-sync rule applies: the connected branch stays working.

**WS-A — Reproducible backend and startup** (`feat/p1-backend-foundation`)
- **Files:** `backend/requirements.txt` (UTF-16 → UTF-8, complete and pinned), new `backend/requirements-dev.txt`, `backend/main.py` (lifespan, health), `backend/search.py` (lazy model and index loading into app state; remove the stray `transformers` import), `backend/config.py`, `.env.example`, both READMEs.
- **Approach:** model, FAISS and CLIP load in `lifespan`. Add `/health/live` and `/health/ready`, which checks the Mongo ping, the model, the index and the manifest. Add a typed settings schema with `APP_ENV`. The app fails fast in non-dev when the JWT secret is the default or shorter than 32 bytes. `ALLOWED_ORIGINS` is parsed from a comma-separated string. There is one DB-name default.
- **Fixes:** C-01, C-06, H-13 (resolves all three unverified claims), M-10.

**WS-B — Security and auth core** (`feat/p1-auth-security`)
- **Files:** `backend/dependencies.py`, `backend/utils/jwt.py`, `backend/utils/security.py`, `backend/api/v1/auth.py`, `backend/models/schemas.py`, `backend/api/v1/intent.py`, new `backend/core/rate_limit.py`, new `backend/core/rbac.py`.
- **Approach:**
  - `is_active` and `token_version` are checked on every authenticated request.
  - JWT claims gain `iat`, `jti` and `role`.
  - A `role` field is added to users. It is additive and defaults to `customer`.
  - Add `require_role()`.
  - Fix the bcrypt pairing, or switch to calling bcrypt or argon2 directly. Existing hashes stay valid.
  - Rate-limit login, signup and the AI endpoints.
  - Remove `purchase` from public events.
  - Put length and size bounds on every request schema.
  - Add security headers middleware.
  - Swagger is off in production.
- **Fixes:** SEC-01, 06, 08, 11, 13 (core), 14, 17; H-01, H-03, M-08.
- **Deferred to Phase 2 (they need email or cookie infrastructure):** email verification, password reset, refresh tokens and HttpOnly cookies.

**WS-C — Canonical catalogue: additive and non-destructive** (`feat/p1-canonical-catalog`)
- **Files:** new `backend/database/migrations/001_canonical_catalog.py`, new `backend/database/indexes.py`, `backend/database/connection.py`, `backend/routes/*` and `backend/api/v1/products.py` (re-point the reads), `backend/search.py` (resolve results by `article_id`).
- **Approach:**
  - New collection `catalog_items`, plus `catalog_variants` if `product_code` grouping is used.
  - It is built from `catalog_products` (read-only source) and the 12 demo `products`.
  - Fields: `article_id`, `product_code`, `name`, `product_type`, `product_group`, `taxonomy_category`, `audience` (from `index_group_name`), `department`, `section`, `garment_group`, `colour` (group, master, value), `pattern`, `description`, `source`, `status`. Plus `price`, `stock` and `images`, which stay **null for H&M** unless D1b synthetic staging data is approved (and then marked `is_synthetic`).
  - **No field is invented.** Fields with no source stay empty, and those items are flagged non-purchasable.
  - `users.email` unique index, catalogue indexes, `$jsonSchema` validators in `moderate` mode.
  - All endpoints read `catalog_items`, and semantic search returns IDs that `GET /products/{id}` can resolve.
- **Fixes:** C-02, C-03 (structure; the real price data waits on D1), H-02, AI-13.

**WS-D — Frontend honesty** (`feat/p1-frontend-honesty`)
- **Files:** `src/lib/api/services.ts`, `src/lib/api/mock.ts` (dev only), `src/routes/{index,search,product.$productId,dashboard,login,visual-search,seasonal}.tsx`, `src/components/cart/cart-sheet.tsx`, `src/lib/api/tracking.ts`.
- **Approach:**
  - Mock data only appears when `VITE_USE_MOCKS=true` (default off), with a visible "Demo data" badge.
  - Real loading, empty, error and retry states.
  - A working "Product not found" page.
  - Remove the fabricated statistics, claims and recommendation reasons, or replace them with real data.
  - Items without a price show "Not available for purchase".
  - Fix the mojibake.
  - Remove `console.log` calls from production builds.
- **Fixes:** C-05, H-08 (removal part), UX-01/03/04/09/16, SEC-24.

**WS-E — Tests, CI and repo hygiene** (`chore/p1-ci-tests`)
- **Files:** `backend/tests/` (moved and new; `conftest.py` with mongomock-motor and a tiny fixture FAISS index), `.github/workflows/ci.yml`, `eslint` and `tsc` scripts, a Playwright smoke spec, `.gitleaks.toml`.
- **Approach:**
  - API-level tests (`httpx.AsyncClient`) for auth, RBAC, products, search and validation.
  - CI runs ruff, pytest, tsc, eslint, build, gitleaks, pip-audit and `bun audit`/osv.
  - **Hygiene, with no deletion of working code:** move the print-only scripts to `backend/scripts/`; delete the `*.backup`/`*.before_relevance_fix` duplicates, the stray root `routes/seasonal.py`, `test_config.py` (which prints secrets) and the legacy `create_embeddings.py`; guard the destructive root `seed.py` behind `--confirm` and `--dry-run` and move it to `scripts/`; take `articles.csv` out of the working tree (Git LFS or object storage plus a download script — **history is not rewritten**).
- **Fixes:** H-11, M-02, M-11, SEC-02/03.

**WS-F — Search evaluation baseline** (`feat/p1-search-eval`)
- **Files:** new `backend/eval/queries.jsonl` (150–300 fashion queries with graded relevance), `backend/eval/run_eval.py`, `backend/eval/README.md`.
- **Approach:**
  - Label the queries using attribute rules from the catalogue columns (type, colour, audience), plus a manually reviewed subset.
  - Metrics: NDCG@10, Recall@100, MRR, zero-result rate, and p50/p95 latency.
  - Include the regression cases from the AI review ("bikini top", "black and white shirt", "black formal shoes for office") and **out-of-catalogue** queries ("laptop", "headphones"), which must return "not carried" rather than near-misses.
- **Output:** a recorded baseline. This workstream changes nothing in the search pipeline.

### 5.2 Order and dependencies inside Phase 1

`WS-A → (WS-B ∥ WS-E) → WS-C → WS-D → WS-F`. WS-D depends on WS-C, because the product pages must resolve real IDs. WS-F needs WS-A to be runnable and WS-C for ID resolution.

### 5.3 Data safety protocol (WS-C), for your approval

1. Take an Atlas snapshot or `mongodump` of `catalog_products`, `products` and `users`. **You** run this, or you approve me running it against staging.
2. `python -m database.migrations.001_canonical_catalog --dry-run`: reads only, writes nothing, and prints counts per source, field-coverage statistics, a sample of 20 transformed documents, and any rejects.
3. You review the report.
4. Run with `--apply` against **staging**. The script is idempotent (upsert by `_id`) and checkpointed. It asserts `count == 105,542 + 12` and verifies a checksum of `catalog_products` before and after (the source is unchanged).
5. Production uses the same command, only after the staging sign-off.
6. **Rollback:** drop `catalog_items`. The source collections are never modified.
7. Creating indexes is non-destructive. The only operation that can *fail* is the unique `users.email` index: if duplicates exist, the script reports them and stops. Nothing is merged or deleted without your approval.

### 5.4 Phase 1 acceptance criteria

- [ ] On a clean machine, following the README: install, import, embed and run. `/health/ready` is green. With the index missing, it is red with a clear reason.
- [ ] `APP_ENV=production` with a default or weak JWT secret → the process exits (test).
- [ ] All three H-13 items are resolved and covered by tests.
- [ ] A deactivated user's token is rejected (test). Non-admin → 403 on a test admin route (test). Login is rate-limited → 429 (test).
- [ ] `/intent/event` rejects `purchase` (test). Oversized payloads → 422 or 413 (tests).
- [ ] Migration: the dry-run report is reviewed. On staging, the counts match, the source checksum is unchanged, and a re-run is a no-op.
- [ ] 200 sampled semantic-search results all resolve via `GET /products/{id}` (no 404s).
- [ ] With the backend down, no mock data appears anywhere (Playwright). An unknown product → "Product not found".
- [ ] `grep` finds no hard-coded business statistics in `src/routes` outside dev and mock code.
- [ ] CI is green on every PR. It fails on a planted fake secret and on a failing test.
- [ ] The eval baseline is recorded, with a committed report and reproducible command.
- [ ] Existing features (search, copilot, stylist, budget, seasonal, visual search, recommendations, auth and profile) still work against the canonical collection. A smoke test covers each one.
- [ ] Git history is intact: no force-push; every change is a reviewed PR.

**Phase 1 completion report.** I will deliver: what changed, the PR links, the test output, the eval baseline, the migration report, any remaining issues, and updated estimates for Phase 2.

---

## 6. Phase 2 — Core E-Commerce

**Objective.** A complete, consistent customer purchase journey on real data from the canonical catalogue, with payments in **sandbox only**.

**Affected areas.** New `backend/api/v1/{cart,checkout,orders,addresses,payments,reviews,coupons,webhooks}.py`; services `pricing`, `inventory`, `order_state`, `notifications`; new collections (`carts`, `orders`, `order_events`, `payments`, `payment_events`, `inventory_reservations`, `addresses`, `coupons`, `reviews`, `audit_log`). Frontend: `/cart`, `/checkout`, `/orders`, `/orders/$id`, `/account/addresses`, `/wishlist`, browse and category pages, variant pickers.

**Approach (key points)**
- **Product model.** `product_code` → product. `article_id` → colour variant. Size SKUs come from the D1 feed. Price, sale price and stock live on the variant or SKU.
- **Server-side pricing.** Pricing is recomputed on the server for every quote: discounts, coupons (with usage limits, validity and minimum order) and shipping (flat or threshold to begin with; pincode serviceability as an extension). GST lines are included if you sell in India. Client-sent prices are never trusted.
- **Cart.** The API is the source of truth. The anonymous cart merges into the user's cart on login, and the wishlist moves to the API.
- **Inventory.** Reservation with a TTL at checkout start; atomic guarded decrement on `paid`; release on failure or expiry; a nightly reconciliation job.
- **Transactions.** Multi-document transactions are used where an order, a payment and stock must change together. Atlas supports these on replica sets.
- **Payments.** Behind a `PaymentGateway` interface, using the sandbox from D3 (test keys and test cards only, never live keys in dev, CI or staging). Webhook signature checks, replay protection and idempotency keys. An order becomes `paid` **only** from a verified webhook.
- **Orders.** State machine `pending_payment → paid → packed → shipped → delivered`, plus `cancelled`, `return_requested → returned → refunded`. Every transition is appended to `order_events`. Cancellation and refunds go through the gateway's sandbox API.
- **Notifications.** Transactional email through a provider interface, with a sandbox or capture inbox outside production. Add email verification and password reset, and move to HttpOnly cookie sessions with refresh rotation (from Phase 1 WS-B).
- **Reviews.** Only verified purchasers can post, and reviews are held for moderation (the moderation UI comes in Phase 4).
- **Staging deployment** is set up in this phase, so the E2E tests run against a real environment.

**Acceptance criteria (summary).**
- The E2E journey passes against staging: Register → Login → Search → Product → Variant → Add to cart → Coupon → Address → Shipping → Sandbox payment → Webhook → Confirmation → Order history → Cancel or return.
- Tampering tests: a modified price or quantity has no effect on the server total.
- 50 concurrent checkouts for 10 units → exactly 10 succeed and stock never goes negative.
- A replayed or invalid webhook has no effect.
- Ownership: a user cannot see another user's cart, order or address.
- No card data or secrets appear in logs, the DB or the repo.
- Every page has loading, empty and error states.

---

## 7. Phase 3 — AI Intelligence

**Objective.** Measurably better discovery, and AI features that only ever describe real catalogue data.

**Approach (in this order: measure, then change)**
1. **Hybrid retrieval.** Keep the MiniLM and FAISS dense retrieval. Add lexical retrieval: Atlas Search (BM25) if your Atlas tier supports it, otherwise a local BM25 index built at embed time. Fuse the two with Reciprocal Rank Fusion. Push metadata filters (category, audience, colour, price, in-stock) into retrieval, using FAISS ID selectors or adaptive over-fetch. Keep the existing reranker, with normalised weights and the parser fixes (AI-08). Move inference into a threadpool, cache query embeddings, and add per-stage timings.
   - **Model upgrades** (for example a stronger embedding model, or a cross-encoder reranker on the top 50) are adopted only if they beat the baseline on the eval set within the latency budget.
2. **Query understanding.** Deterministic extraction of budget ("under ₹3,000"), colour, type, audience, occasion and use case, with a mapping table (formal/office → pumps, loafers, flat shoes, shirts, blazers). The LLM (D4) is an optional enhancer that outputs **structured filters only**. When the LLM fails, the deterministic parser is used instead. If a query is outside the catalogue, the system says "not carried" instead of returning near-misses.
3. **Shopping Copilot.** A tool-calling agent. Its only tools are `search_products`, `get_product`, `compare_products`, `check_stock`, `get_price` and `similar_products`, all backed by the real APIs.
   - Every product, price and attribute in an answer must come from a tool result. The server validates IDs and prices in the response and removes anything it cannot verify.
   - It asks a clarifying question when constraints are missing or conflicting.
   - Session memory is kept server-side with a TTL and covers size, budget and preferences within the session only. Persisting across sessions needs an explicit opt-in.
   - Responses stream.
4. **AI Stylist.** Outfit composition across the whole catalogue (not 500 documents), using category slots (top, bottom, shoes, accessory). Colour coordination rules on `colour_master` and `pattern`, occasion and season context, a budget constraint (once prices exist), and wardrobe items entered by the user. Every item links to a real product.
5. **Budget Optimizer.** Priority-weighted selection under a total budget, using a small knapsack or DP over shortlisted candidates. It reports utilisation, alternatives and the total, using real prices only. It is disabled for items with no price.
6. **Visual Search.** An offline CLIP image-embedding job over the catalogue images (once images exist; D1). A separate FAISS image index with a manifest. The request path is: validate, strip EXIF, cap pixels, one embedding, one search. Uploads are not stored by default (privacy). Add a "search within category" option.
7. **Recommendations, matched to the data that exists:**
   - content-based similarity (now);
   - session-based, from `session_events` (now);
   - popular and trending, from views and orders (Phase 2 onwards);
   - "frequently bought together", only once enough orders exist (gated by a minimum support threshold);
   - no collaborative filtering until there is enough data.
   Each surface records impressions and clicks for analytics.
8. **AI reliability and cost** (§15 of the brief):
   - a provider interface with a timeout, retries with jitter, and a circuit breaker;
   - one fallback provider is optional; the deterministic path is mandatory;
   - a response cache keyed on normalised input;
   - per-user and per-IP quotas;
   - token and cost logging, with a daily cost cap that degrades gracefully;
   - no LLM call for queries the deterministic parser handles with high confidence;
   - streaming for the copilot.

**Acceptance criteria (summary).**
- NDCG@10 and Recall@100 ≥ the Phase 1 baseline, with a CI gate that fails on regression.
- Constraint-satisfaction rate ≥ 95 % on queries with explicit colour, type or price.
- Out-of-catalogue queries return "not carried".
- Copilot grounding test: 0 product IDs or prices in 200 scripted conversations that do not exist in the DB.
- With the LLM disabled or failing, every feature still works.
- Search p95 latency is within the agreed budget under load.
- Visual search makes zero outbound fetches per request.

---

## 8. Phase 4 — Admin and Business Operations

**Objective.** Operators can run the store without touching the database, and every metric is real.

**Scope.**
- A role-gated admin app (`/admin`, separate layout, admin MFA). The backend enforces RBAC on every route, never the frontend alone.
- Products: CRUD; CSV import with a dry-run and validation report; image upload via signed URLs to object storage with automatic thumbnails; variant and stock editing; re-embedding on change, through a background job and an index update.
- Categories and brands.
- Inventory with history and low-stock alerts.
- Orders: status changes, cancellation, sandbox refunds.
- Customers: view and deactivate.
- Coupons.
- Review moderation.
- Audit-log viewer.
- **Analytics** from real queries only: sales, AOV, conversion funnel, top products, search analytics (top queries, zero-result queries, click-through), and recommendation analytics (CTR by surface).
- The existing `/dashboard` becomes this real analytics view, or is removed.

**Acceptance criteria (summary).**
- Every admin API returns 403 for customers (tests).
- The admin E2E passes: create a product with an image → it appears in search after re-indexing → stock it → a customer buys it → admin ships the order → refund in sandbox. Each step appears in `audit_log`.
- Dashboard figures reconcile with direct DB queries in a test.

---

## 9. Phase 5 — Quality and Production

**Objective.** Deploy reliably at reasonable cost, and be able to operate, observe and recover.

**Recommended cost-effective architecture** (to confirm under D5; check current pricing before committing):

| Component | Recommendation | Why |
|---|---|---|
| Frontend (TanStack Start SSR) | A managed platform with Nitro or TanStack support (for example Vercel, Netlify or Cloudflare) | Zero-ops HTTPS, CDN and preview deploys |
| API | **One container service with ≥2 GB RAM** (for example Google Cloud Run, Render or Fly.io), with the models and FAISS index **baked into the image** or pulled from object storage at boot | MiniLM, the ~162 MB index and CLIP must be resident in memory; serverless functions with cold starts suit this badly |
| Background jobs | The same image, run as a worker or scheduled job: embeddings, reconciliation, emails | No extra platform |
| Database | MongoDB Atlas, on a dedicated tier for production (backups and PITR). As far as I know, the free tier lacks the backup features needed. | Keep Mongo; there is no technical reason to replace it |
| Images | S3-compatible object storage plus a CDN with resizing | Cheap; removes the third-party hot-linking |
| Secrets | The platform's secret store, separate per environment | — |
| Observability | Structured logs; error tracking (for example Sentry, free tier); uptime checks; basic metrics | Low cost, enough for launch |
| CI/CD | GitHub Actions: test → build image → deploy to staging → manual promote to production; rollback to the previous image | — |

**Not recommended yet:** Kubernetes, a separate vector database, microservices, GPU hosting. Exact FAISS over about 100k vectors is fast on CPU; revisit only if measurements show a need.

**Scope.**
- Load and soak tests.
- Chaos checks (the DB, LLM, FX service, gateway or CDN being down).
- Lighthouse and axe with a CI budget.
- WCAG 2.2 AA pass.
- Premium UI polish: design tokens, typography, product cards and pages, skeletons, mobile.
- External security scan, or an OWASP ASVS L1 review.
- Backup restore drill with documented RPO and RTO.
- Runbooks.
- Domain, HTTPS and HSTS.
- SEO: sitemap, `Product` structured data, canonical URLs.
- Documentation.

**Acceptance criteria (summary).**
- Production is deployed from a tagged commit, and rollback is shown to take under 15 minutes.
- The restore drill passes.
- The load test passes at 2× the expected peak with < 1 % errors.
- Alerts fire in a game-day test.
- The Security review §12 gate is fully passed.
- No open Critical or High findings remain.

---

## 10. Extra features I recommend (you didn't list these, and they earn their place)

| Feature | Value | Phase |
|---|---|---|
| Search analytics and zero-result log | The cheapest relevance signal; feeds the eval set | 1 (logging), 4 (UI) |
| Feature flags | Safe incremental rollout of each phase | 1 |
| Idempotency keys on all writes | Prevents duplicate orders and payments on retry | 2 |
| Size guide plus size on SKUs, with "notify me" back-in-stock | Fashion's biggest conversion and return lever | 2 |
| Pincode serviceability and delivery-date estimate (India) | Reduces checkout abandonment | 2 |
| GST-compliant invoices (if selling in India) | Legal requirement for taxable sales; confirm with your accountant | 2 |
| Recently viewed and "continue shopping" | Cheap personalisation from existing session data | 3 |
| "Not carried" responses for out-of-catalogue queries | Trust; prevents laptop-bag answers | 3 |
| Low-stock and price-drop alerts on the wishlist | Re-engagement without ads | 4 |
| Consent banner and data export/deletion (DPDP Act / GDPR) | Compliance | 2 |
| SEO structured data and sitemap | Organic traffic | 5 |

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| No real goods or licence for the catalogue (§1.2) | D1 decision now; schema ready for your own feed; H&M kept as labelled demo data |
| I cannot run tests in this session (§1.3) | A2 (network) or you run the commands; nothing is marked done without real test output |
| Relevance regressions | Eval baseline in Phase 1; CI gate in Phase 3 |
| Lovable sync conflicts | Small PRs; the connected branch stays green; follow `AGENTS.md` |
| Scope size (the brief describes a full commercial platform) | Phase gates, D6 release scope, feature flags; every phase delivers usable value |
| LLM cost or hallucination | Tool-grounding, server-side validation of answers, quotas, deterministic fallback |

---

## 12. Approval requested

To start Phase 1 I need:
1. **Approval of Phase 1 scope** (§5) and of the **data-safety protocol** (§5.3).
2. **A1:** push access, so I can open feature-branch PRs.
3. **A2:** package installs allowed (network on, in a new chat), so I can run tests myself. Otherwise you run the commands I give you.
4. **D7**, and your direction on **D1/D1b** (labelled demo catalogue plus your own product feed later; synthetic staging prices yes or no).

I'll start with WS-A and finish each workstream with a short report: what changed, the test results, and what remains.
