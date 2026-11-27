# CatalogIQ AI — Phase 1 Execution Plan and Status

Branch: `feat/p1-backend-foundation` (from `main` @ `5d7ba72`). Phase 2 does not start until Phase 1 is completed, tested, reviewed and approved.

## Your conditions and how each is enforced

| # | Condition | How it is enforced |
|---|---|---|
| 1 | Preserve the catalog and working features | No script in Phase 1 writes to `catalog_products` or `products`. Every behaviour change has a regression test. |
| 2 | Additive DB changes only | New collection (`catalog_items`) and new indexes only. No updates, deletes or drops on existing collections. |
| 3 | Dry run first | The migration defaults to `--dry-run`. `--apply` refuses to run without a dry-run report hash. |
| 4 | No catalog modification without approval | The only write path into existing data is the unique `users.email` index. If duplicates exist it **stops and reports**; it never merges. |
| 5 | CI, tests, security, roles, eval baseline in Phase 1 | WS-B, WS-E and WS-F below |
| 6 | Python 3.11 | All backend code compiles under 3.11 (checked). Dependency compatibility is confirmed by the install step in §3. |
| 7 | Keep the frontend toolchain | **No change.** Both `package-lock.json` and `bun.lock` stay untouched. CI will use whichever you confirm you use (question below). |
| 8 | Synthetic prices: dev/staging only, labelled | Stored as `is_synthetic: true` with `source: "synthetic_demo"`. The API refuses to serve them when `APP_ENV=production` (test-enforced). The UI shows a "Demo price" badge. |
| 9 | H&M stays demo-only | `source: "hm_demo"` and `purchasable: false` in production. Never counted as inventory. |
| 10 | No real payments | Nothing payment-related exists in Phase 1. |
| 11 | Feature branch, logical commits | One branch per workstream; commits are scoped and messages reference finding IDs; no history rewrites. |

**Question (affects WS-E only):** Do you install the frontend locally with `npm` or `bun`? Both lockfiles came in the initial Lovable commit and `package.json` has not changed since, so both are currently consistent. I will run CI with the one you use and leave the other untouched.

---

## 1. Phase 1 workstreams

Workstreams run in this order: WS-A, then WS-B and WS-E in parallel, then WS-C, WS-D and WS-F. Each one becomes a PR.

### WS-A — Reproducible backend and startup ✅ code complete, awaiting your local test run

| Task | Files |
|---|---|
| Re-encode `requirements.txt` from UTF-16 to UTF-8; keep all 37 existing pins; add the missing ML packages | `backend/requirements.txt`, `backend/requirements-dev.txt` |
| Comma-separated `ALLOWED_ORIGINS`; validate origins; refuse a placeholder or short JWT secret or a `*` origin outside dev; no secrets in error output; dev defaults unchanged | `backend/config.py`, `backend/.env.example` |
| Model and index load in the lifespan, not at import; missing index → 503 rather than a crash; inference off the event loop; results unchanged | `backend/search.py`, `backend/main.py` |
| `/health/live`, `/health/ready`; `/health` unchanged | `backend/main.py` |
| Remove the stray `transformers` audio import | `backend/services/semantic_reranker.py` |
| Ignore the generated index files | `.gitignore` |
| Tests (27 functions, 31 cases) | `backend/tests/{conftest,test_settings,test_search_engine,test_health}.py`, `backend/pytest.ini` |
| Docs | `backend/README.md` |

### WS-B — Auth, security and basic customer/admin roles

| Task | Files |
|---|---|
| Check `is_active` and `token_version` on every authenticated request | `backend/dependencies.py`, `backend/utils/jwt.py` |
| `role` field (additive; missing role = `customer`), `require_role("admin")`, JWT `iat`/`jti`/`role` | `backend/core/rbac.py` (new), `backend/api/v1/auth.py`, `backend/models/schemas.py` |
| Fix the passlib/bcrypt incompatibility **if your test run confirms it**, keeping existing hashes valid | `backend/utils/security.py`, `requirements.txt` |
| Rate limits on login/signup (strict) and AI endpoints (moderate); in-memory for now, Redis-ready interface | `backend/core/rate_limit.py` (new), the affected routers |
| `/intent/event` stops accepting `purchase` from clients | `backend/models/schemas.py`, `backend/api/v1/intent.py` |
| Length and size bounds on all request bodies | `routes/stylist.py`, `routes/semantic_search.py`, `api/v1/budget_optimizer.py`, `schemas.py` |
| Security headers middleware; Swagger disabled when `APP_ENV=production` | `backend/main.py` |
| Tests: deactivated-token rejection, 403 for a customer on an admin route, 429 on brute force, `purchase` rejected, oversized → 422 | `backend/tests/test_auth_security.py`, `test_rbac.py`, `test_rate_limit.py`, `test_validation_bounds.py` |

Admin accounts are created only by a CLI script that **you** run (`python -m scripts.grant_role --email you@x --role admin`). Nothing can be self-promoted through the API.

### WS-C — Canonical catalogue (additive)

| Task | Files |
|---|---|
| Read-only data-profile script: field coverage, counts, duplicates, DB name check | `backend/scripts/profile_catalog.py` (new) |
| Migration `001`: builds the **new** `catalog_items` from `catalog_products` + `products`; `--dry-run` is the default; idempotent upserts into the new collection only; count and source-checksum assertions | `backend/database/migrations/001_canonical_catalog.py` (new) |
| Optional synthetic prices and stock for dev/staging (`--synthetic-prices`; refused when `APP_ENV=production`) | same script |
| Indexes on the new collection; unique `users.email` (stops on duplicates) | `backend/database/indexes.py` (new) |
| Read paths can switch to `catalog_items` behind `CATALOG_COLLECTION` (default stays `catalog_products` until you approve the switch) | `backend/search.py`, `api/v1/products.py`, `routes/*`, `services/product_service.py` |
| Tests on an in-memory fake DB: transform correctness, idempotency, production refuses synthetic data, source untouched | `backend/tests/test_migration_001.py` |

### WS-D — Frontend honesty (no redesign)

| Task | Files |
|---|---|
| Mock fallback only when `VITE_USE_MOCKS=true`, with a visible "Demo data" badge | `src/lib/api/services.ts`, `src/lib/api/client.ts`, `src/lib/api/mock.ts` |
| Real loading, empty, error and retry states; a "Product not found" page | `src/routes/{search,product.$productId,index,visual-search}.tsx` |
| Remove the fabricated dashboard, landing and login statistics and claims | `src/routes/{dashboard,index,login}.tsx` |
| "Demo price" badge for synthetic data; "Not available for purchase" when there is no price | product card, product page, `cart-sheet.tsx` |
| Fix the mojibake; remove production `console.log` | `src/routes/seasonal.tsx`, `src/lib/api/tracking.ts` |

### WS-E — CI, tests and repo hygiene (nothing working is deleted)

| Task | Files |
|---|---|
| Move the legacy root `test_*` / `check_*` scripts to `backend/scripts/`; move the 5 real test files to `backend/tests/` | `backend/` |
| Delete `test_config.py`, which prints secrets (git history keeps it) | `backend/test_config.py` |
| Delete the `*.backup` / `*.before_relevance_fix` copies and the unused root `routes/seasonal.py` (after a diff confirms they are unused) | listed files |
| Guard the destructive `import_hm_catalog.py` and root `seed.py`: `--dry-run` default, `--i-understand-this-deletes` flag, refuse in production | `backend/database/import_hm_catalog.py`, `seed.py` |
| GitHub Actions: ruff, pytest (3.11), frontend lint + typecheck + build, gitleaks, pip-audit, npm/bun audit | `.github/workflows/ci.yml`, `.gitleaks.toml`, `backend/ruff.toml` |
| `articles.csv` (in git) stays as it is for now; moving it to LFS is optional and needs your approval | — |

### WS-F — Search quality baseline (measures only; changes no search behaviour)

**Baseline v0 (manual, by owner, 2026-11-27) recorded with root-cause analysis and the proposed S1–S9 improvements in [`backend/eval/BASELINE.md`](backend/eval/BASELINE.md).** The S-changes are query-time only, behind `SEARCH_RERANK_VERSION=v2` (default `v1`), and wait for your approval.

| Task | Files |
|---|---|
| 150–300 fashion queries with graded labels derived from catalogue attributes, plus a hand-reviewed subset; regression cases; out-of-catalogue cases (laptop, headphones) | `backend/eval/queries.jsonl` |
| Runner: NDCG@10, Recall@100, MRR, zero-result rate, constraint-satisfaction, p50/p95 latency, JSON + Markdown report | `backend/eval/run_eval.py`, `backend/eval/README.md` |
| Baseline report committed | `backend/eval/reports/baseline.md` |

---

## 2. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| **I can't run tests in this session.** Packages can't be installed (network off), so nothing can execute. | Certain | You run the §3 commands and paste the output. I mark each workstream "awaiting verification" until then. Alternatively, enable package installs and start a new chat. |
| **I can't push.** The repo is attached read-only. | Certain | I deliver a git bundle (§4) that you fetch locally and push. Or grant push access and I open PRs. |
| Your `.env` sets `ALLOWED_ORIGINS` without `http(s)://`, or `APP_ENV` is non-dev with a weak secret, so the API **now refuses to start** | Low | Intended: the error message says exactly what to fix, and secrets are never printed |
| Some pinned versions (for example `cryptography==50.0.0`) may not resolve on Python 3.11 | Unknown | The install step in §3 confirms it. If anything fails I'll adjust only that pin |
| passlib 1.7.4 + bcrypt 5.0.0 is likely incompatible, so `test_auth.py` may fail at hashing | Medium | That's an existing defect, now surfaced. WS-B fixes it with existing hashes kept valid |
| `DATABASE_NAME` case mismatch (code `CatalogIQ` vs old example `catalogiq`) | Medium | Defaults unchanged; `/health/ready` now shows the catalogue count so a wrong name is obvious |
| `import_hm_catalog.py` wipes `catalog_products` if someone runs it | Existing | Warned in the README now; guarded in WS-E |
| `/health/ready` reveals counts and error text publicly | Low | Acceptable for now; restricted at the edge in Phase 5 |
| Lovable sync conflicts | Medium | Small PRs into a feature branch; `main` stays working |

---

## 3. Commands for you to run locally (WS-A verification)

All of these are read-only towards MongoDB.

```bash
# 0. Get the branch (see §4 if you received the bundle)
cd catalog-iq-ai
git fetch ../catalogiq-phase1.bundle feat/p1-backend-foundation:feat/p1-backend-foundation
git checkout feat/p1-backend-foundation

# 1. Fresh Python 3.11 environment (does not touch your existing venv)
cd backend
python3.11 -m venv .venv-p1
source .venv-p1/bin/activate            # Windows: .venv-p1\Scripts\activate
python --version                        # expect 3.11.x
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt 2>&1 | tail -20

# 2. Record exact versions so I can pin the ML packages
pip freeze | grep -iE "^(faiss-cpu|sentence-transformers|torch|transformers|numpy|pandas|pillow|bcrypt|passlib)=="

# 3. New tests (no DB, no network, no index needed)
pytest -q tests

# 4. Existing safe tests (mocked; test_auth reveals the bcrypt question)
pytest -q test_auth.py test_copilot_validation.py test_intent_event_validation.py \
          test_recommendation_filtering.py test_semantic_reranker_relevance.py

# 5. Config checks (H-13); these print no secrets
ALLOWED_ORIGINS="http://a.test,http://b.test" python -c "from config import settings; print(settings.allowed_origins)"
python -c "from config import settings; print('db name:', settings.database_name, '| env:', settings.app_env)"
APP_ENV=production JWT_SECRET=short python -c "import config" 2>&1 | tail -1   # expect: Unsafe configuration ...

# 6. Real startup against YOUR database (reads only: ping, count, index files)
uvicorn main:app --port 8000
# in another terminal:
curl -s localhost:8000/health
curl -s localhost:8000/health/ready | python -m json.tool
curl -s -X POST localhost:8000/api/semantic-search -H 'content-type: application/json' \
     -d '{"query":"black dress","top_k":5}' | head -c 600; echo
```

**Please paste back:** the output of steps 2–5, the JSON from `/health/ready`, and whether the semantic-search call returned products as it did before.

## 4. Getting the commits

The bundle `catalogiq-phase1.bundle` contains branch `feat/p1-backend-foundation`: 6 commits on top of `main@5d7ba72`, and no history rewrites. Step 0 above fetches it. After you review it, `git push -u origin feat/p1-backend-foundation` and open a PR to `main`. If you'd rather review without git, use the patch files (`000X-*.patch`, applied with `git am`).

## 5. Phase 1 acceptance criteria (exit gate)

- [ ] Clean Python 3.11 install from `requirements.txt` succeeds; ML versions pinned *(WS-A)*
- [ ] API starts without the index; `/health/ready` 503 with a reason; with the index, 200 and semantic results unchanged *(WS-A)*
- [ ] Production config with a weak or placeholder secret, or a `*` origin, refuses to start, without printing secrets *(WS-A)*
- [ ] Deactivated user's token rejected; customer → 403 on admin route; brute force → 429; `purchase` event rejected; oversized bodies rejected *(WS-B)*
- [ ] Existing users can still log in with their existing passwords *(WS-B)*
- [ ] Data-profile report reviewed by you; migration dry-run report reviewed; on staging, `catalog_items` = 105,542 + 12, source checksum unchanged, re-run is a no-op *(WS-C)*
- [ ] Synthetic prices impossible to serve with `APP_ENV=production` (test) *(WS-C)*
- [ ] 200 sampled semantic results all resolve on the product endpoint *(WS-C)*
- [ ] Backend down → no mock data shown (unless `VITE_USE_MOCKS=true`, with badge); unknown product → "not found"; no hard-coded business statistics *(WS-D)*
- [ ] CI green on the PR; fails on a planted fake secret and a failing test *(WS-E)*
- [ ] Bare `pytest` is safe: no DB or network access during collection *(WS-E)*
- [ ] Search baseline report committed and reproducible *(WS-F)*
- [ ] Smoke test for every existing feature passes; git history intact *(all)*
