# CatalogIQ AI — Security Review

Commit audited: `5d7ba72`. Companion to [CATALOGIQ_AUDIT.md](CATALOGIQ_AUDIT.md) (IDs `C-/H-/M-/L-`); `SEC-` IDs are local to this review.

**Method / limits.** Manual source review plus a pattern scan of the full git history (39 commits). No dynamic testing, no penetration test, no dependency-vulnerability scan (`pip-audit`/`npm audit` need network, unavailable). Dependency statements below are therefore *"to my knowledge — verify with a scanner"*. Nothing in this review touched a live system, credentials or production data, and **no real payment credentials were used or are needed** (the payment section is a design for *test-mode* integration only). This is an engineering review, not legal advice.

---

## 1. Summary

| Area | Posture |
|---|---|
| Secrets in repo/history | **No real secrets found** (details §2). `.env` is git-ignored. Placeholders only. |
| Authentication | Sound primitives (bcrypt, JWT, uniform login error) but **unsafe defaults** (default signing key), no lockout, no verification/reset/revocation |
| Authorization | **Absent** — no roles, almost no protected endpoints |
| Abuse resistance | **None** — no rate limiting; expensive anonymous endpoints |
| Input validation | Good on auth/copilot/visual-search; **missing bounds** on several JSON bodies |
| Injection | Low risk observed: all query values are typed `str`/`float`; user text is regex-escaped before use in Mongo regex |
| Web client security | Token in `localStorage`, no CSP/security headers configured, React escaping prevents obvious XSS (the only `dangerouslySetInnerHTML` is the stock shadcn chart `<style>` in `src/components/ui/chart.tsx:73`, fed by developer-supplied colour config, not user input; keep it that way and avoid adding others) |
| Payments | Not implemented; design guidance in §6 |
| Operations/monitoring | No security logging, alerting or audit trail |

---

## 2. Secrets and configuration

| ID | Sev | Finding | Evidence | Fix | Pri |
|---|---|---|---|---|---|
| SEC-01 (=C-06) | Critical | **Default JWT secret `change-me-secret`** is used silently when `JWT_SECRET` is unset; repo is public, so anyone can mint valid tokens for any `sub` on such a deployment. | `backend/config.py:31-34` | Refuse to start when `APP_ENV != "development"` and secret is default or < 32 bytes; generate with `openssl rand -base64 48`; support two keys for rotation (`kid`). | P0 |
| SEC-02 | Medium | **Credential-bearing config is echoed.** `test_config.py` prints the Mongo URL and JWT secret at pytest collection time (CI logs, terminals); `create_embeddings.py:17` prints `settings.mongodb_url` (Atlas URLs embed the password). | `backend/test_config.py:3-5`; `backend/create_embeddings.py:17` | Delete `test_config.py` (or assert without printing); never print URLs; if a real `.env` was ever shared or logged, **rotate** the Atlas user password and JWT secret. | P1 |
| SEC-03 | Info | **History scan found no committed credentials.** Pattern scan over all commits for Atlas URIs with credentials, Google API keys (`AIza…`), `sk-…` keys, private-key blocks and `JWT_SECRET=` assignments: the only hit was the `.env.example` placeholder text in the initial commit. Patterns are heuristic — run `gitleaks`/`trufflehog` in CI to be sure, and treat any credential that ever lived in a local `.env` you screen-shared as exposed. | `git log -p` scan | Add secret scanning to CI and a pre-commit hook. | P1 |
| SEC-04 | Medium | **Inconsistent config surface**: DB name default `CatalogIQ` (`config.py:25`) vs `catalogiq` in `.env.example:3`; root `seed.py` reads `MONGO_URI` (a different variable) and hard-codes DB/collection; `ALLOWED_ORIGINS` documented as comma-separated but typed `list[str]` (UNVERIFIED parse failure, H-13). | as listed | One documented schema, validated at start-up, with environment-specific examples. | P1 |
| SEC-05 | Medium | **Swagger/ReDoc enabled unconditionally** (`main.py:54-55`) — useful in dev, discloses the full surface in prod. | `main.py` | Disable or protect in production. | P2 |

**Secrets management target:** platform secret store (not files), separate secrets per environment, least-privilege Atlas user (readWrite on the app DB only, no admin), Atlas IP allow-list/private networking, TLS everywhere, rotation runbook.

---

## 3. Authentication and session management

| ID | Sev | Finding | Evidence | Fix | Pri |
|---|---|---|---|---|---|
| SEC-06 | High (=H-01) | **No rate limiting / lockout** on login or signup; bcrypt is CPU-costly so unauthenticated flooding is also a cheap DoS. | `api/v1/auth.py`; no limiter anywhere | Per-IP and per-account throttles with backoff (e.g. 5/min/account, 20/min/IP), CAPTCHA/step-up after repeated failures, edge rate limiting. | P1 |
| SEC-07 | High (=H-14) | **Incomplete account lifecycle.** No email verification (signup issues a token immediately), no password reset/change, no logout/revocation, no refresh, no MFA option. 24 h bearer token. | `auth.py:53-57`; `config.py:37` | Verification + reset via signed one-time tokens; short-lived access token (≤15 min) + rotating refresh with reuse detection; `token_version` on the user for global logout. | P1 |
| SEC-08 | High | **Deactivated users keep access** with an existing token: only `/auth/login` checks `is_active`; `get_me` and `update_profile` do not, and `verify_token` never consults the database. | `auth.py:79-83` vs `:97-124, :132-172`; `dependencies.py:23-47` | Check `is_active` (and `token_version`) in `get_required_user` (cache briefly). | P0 |
| SEC-09 | Medium (=H-14) | **Bearer token stored in `localStorage`** and attached by an Axios interceptor — any XSS exfiltrates it. | `src/lib/api/auth.ts:33-44`; `client.ts:13-19` | HttpOnly+Secure+SameSite=Lax cookie (then add CSRF protection), or keep memory-only access token + refresh cookie. | P1 |
| SEC-10 | Medium | **Weak claims.** Only `sub`, `email`, `exp`; no `iat/jti/iss/aud/role`; HS256 shared secret; `python-jose==3.3.0` is a little-maintained library which, to my knowledge, has published advisories (e.g. algorithm-confusion and JWE-decompression issues fixed in later releases; the app uses HS256 with a pinned `algorithms` list, which limits exposure) — verify. | `utils/jwt.py`; `requirements.txt` | Add claims; consider `PyJWT` or `authlib`; scanner in CI. | P2 |
| SEC-11 | Medium (UNVERIFIED) | **bcrypt/passlib compatibility.** `passlib==1.7.4` with `bcrypt==5.0.0` is expected to fail or warn at hash time (passlib's bcrypt probe uses a >72-byte secret, rejected by bcrypt ≥5). Also bcrypt silently truncates at 72 bytes while the API accepts up to 128 characters. | `requirements.txt` (decoded from UTF-16), `schemas.py:9`, `utils/security.py` | Run the one-line check in H-13; call `bcrypt` directly with pre-hash (SHA-256 → base64) or use argon2id; cap/normalise password bytes. | P0 verify |
| SEC-12 | Low (=L-04) | Timing/enumeration: unknown email returns faster than wrong password; signup returns 409 for existing emails. | `auth.py:32-37, :70-77` | Constant-time dummy hash; generic signup response once email verification exists. | P3 |

---

## 4. Authorization and data access

| ID | Sev | Finding | Evidence | Fix | Pri |
|---|---|---|---|---|---|
| SEC-13 (=C-04) | Critical | **No role model or admin plane.** Nothing prevents a future admin route from being public; no `require_role`, no ownership checks, no audit log. | `dependencies.py`, `utils/jwt.py` | Roles (`customer`,`admin`,`staff`), `require_role` dependency, resource-ownership checks on carts/orders/addresses, append-only `audit_log`, MFA for admins, separate admin origin. | P0 with Phase 2/3 |
| SEC-14 (=H-03) | High | **Anonymous event ingestion lets anyone forge behaviour**, including `purchase` (weight 10), for any `session_id` (client-chosen, guessable if leaked). Pollutes personalisation and, later, analytics/revenue attribution. | `api/v1/intent.py:35-67`; `schemas.py:104-117`; `session_intent_service.py:6-12` | Remove `purchase` from the public enum (emit server-side from paid orders); issue `session_id` server-side (signed, HttpOnly); per-session event cap and rate limit; validate `product_id` exists. | P1 |
| SEC-15 | Medium | **Expensive anonymous AI endpoints.** `/semantic-search`, `/copilot/chat`, `/visual-search`, `/stylist`, `/budget` require no auth or quota; `/visual-search` does up to 100 outbound fetches + 100 model passes per call. | `routes/*`, `api/v1/budget_optimizer.py` | Rate limit and (optionally) require a lightweight anonymous token; hard concurrency limit on the inference pool; WAF bot rules. | P1 |
| SEC-16 | Medium | **Mass-assignment is handled well** (`UpdateProfileRequest` whitelist, `extra` default ignore) — keep this pattern for new endpoints; make `Config.extra = "forbid"` on money-related schemas. | `schemas.py:51-54`, `auth.py:153-159` | — | P3 |

---

## 5. Input validation, injection and file handling

| ID | Sev | Finding | Evidence | Fix | Pri |
|---|---|---|---|---|---|
| SEC-17 | Medium (=M-08) | **Unbounded request fields:** `StylistPayload.notes` and strings, `SearchRequest.query`, `IntentPayload.query`, `BudgetPayload.categories` (list of arbitrary length → one compiled regex each), `BudgetPayload.budget`/`StylistPayload.budget` (no upper bound). Allows memory/CPU amplification. | `stylist.py:12-17`; `semantic_search.py:20-23`; `budget_optimizer.py:11-14` | `max_length`, list `max_length`, numeric `le`; global body-size limit at the proxy (e.g. 1 MB for JSON, 8 MB for the upload route only). | P1 |
| SEC-18 | Low | **NoSQL injection: no issue found.** Inputs reach Mongo as typed strings/floats; Mongo operators cannot be smuggled through Pydantic `str` fields; the one regex built from user input is escaped (`re.escape`, `budget_optimizer.py:41`) and anchored. Keep Pydantic types strict for any new filter DSL. | — | — | — |
| SEC-19 | Medium (=M-13) | **Image upload / remote fetch hardening.** Good: MIME allow-list, 8 MB cap, Pillow format check, empty-file check. Gaps: no `Image.MAX_IMAGE_PIXELS` policy (decompression-bomb within 8 MB), no EXIF stripping, catalog image fetches follow redirects with no response-size cap and no host allow-list (SSRF-adjacent: URLs come from the DB today; once admins upload or import URLs this becomes exploitable). | `routes/visual_search.py:18-22, 70-86, 117-130` | Pixel cap + `Image.verify()`; remove runtime fetching (index offline); if fetching remains, allow-list hosts, block private IP ranges, cap bytes/redirects. | P1 |
| SEC-20 | Low | **Regex use on large text** in reranker/recommendation paths with user-influenced terms is `re.escape`d — no ReDoS observed, but 3,000+ lines of regex/loop logic run per request on the main thread (availability, see AI review H-07). | `services/*` | Cap query length; move heavy paths to a worker. | P2 |

---

## 6. Web client and transport

| ID | Sev | Finding | Fix | Pri |
|---|---|---|---|---|
| SEC-21 | Medium | **No security headers / CSP configured anywhere** (the TanStack server adds only an error page and CSRF middleware for server functions, `start.ts`). Needed: `Content-Security-Policy` (restrict `img-src` to the image CDN, `connect-src` to the API), `Strict-Transport-Security`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `frame-ancestors`. | Configure at the edge/server; test with report-only first. | P1 |
| SEC-22 | Low | **CORS** posture is correct in principle (explicit origin list, credentials true) but `allow_methods=["*"]`, `allow_headers=["*"]`; production origins must be supplied through a parseable setting (H-13). | Restrict to needed methods/headers; verify preflight in staging. | P2 |
| SEC-23 | Low | **Third-party resource loading**: Google Fonts, Unsplash images. Privacy leak of visitor IP/UA to third parties; supply-chain dependency. | Self-host fonts; serve images from your own CDN. | P3 |
| SEC-24 | Medium | **Verbose client logging** of every tracking event and the API base URL (`tracking.ts:30-31,36`). | Remove in production builds. | P2 |
| SEC-25 | Low | `robots.txt` allows all paths including account pages; no `noindex` on private routes. | Disallow `/profile`, `/dashboard`, `/checkout`, `/orders`, `/admin`. | P3 |

---

## 7. Dependencies and supply chain

- **Python:** `fastapi==0.115.0` / `starlette==0.38.6`, `python-multipart==0.0.9`, `python-jose==3.3.0`, `ecdsa==0.19.2`, `cryptography==50.0.0`, etc. The file is **UTF-16** and misses all ML libraries (C-01), so the *real* dependency set is undocumented. To my knowledge, advisories have been published against older Starlette multipart handling and `python-multipart` versions of this vintage (relevant because `/visual-search` parses uploads) — **run `pip-audit` and upgrade**; this was not verified offline.
- **JavaScript:** both `bun.lock` and `package-lock.json` are committed — pick one package manager so CI and local installs resolve identically. `bunfig.toml` has a 24 h minimum-release-age guard, a good supply-chain control. Run `npm audit`/`osv-scanner` in CI.
- **Models:** `SentenceTransformer("all-MiniLM-L6-v2")` and CLIP download from the Hugging Face hub at runtime. Pin revisions, vendor into the image, and load with `local_files_only=True` in production. `pickle.load` is used for `hm_product_ids.pkl` (`search.py:26-27`): safe only because the artefact is self-built — never load pickles from user or untrusted sources; prefer JSON/NumPy for the ID map.
- **CI hygiene:** Dependabot/Renovate, lockfile integrity checks, SBOM generation.

---

## 8. Payments (design guidance — nothing implemented today)

**Rules for development: never use real payment credentials, never run a real transaction. Use the gateway's test mode and test cards only.**

1. **Scope minimisation (PCI):** use the gateway's hosted checkout / hosted fields so card data never touches your servers or logs. Your API stores only gateway customer/payment IDs and last-4/brand if needed.
2. **Server is the source of truth:** the browser sends `(product_id, qty, variant)`; the server recomputes prices, tax, shipping, discounts and currency (H-09). Never trust `price` from the client or from `localStorage`.
3. **Idempotency:** `Idempotency-Key` on checkout-start and payment-intent creation; unique index on `(user_id, idempotency_key)`.
4. **Webhooks:** verify signature, reject replays (timestamp tolerance), process idempotently (store event IDs), return 2xx quickly, reconcile asynchronously; order becomes `paid` **only** from a verified webhook.
5. **Inventory consistency:** reserve stock at checkout-start with TTL; decrement atomically on `paid` using `findOneAndUpdate` with a `stock_qty >= qty` guard; release on expiry/failure; nightly reconciliation job.
6. **Fraud/abuse:** rate-limit checkout, velocity checks, address/IP mismatch signals via the gateway's radar tools, admin review queue.
7. **Records:** append-only `order_events`, `payment_events`, and `audit_log`; retention policy.
8. **Refunds/returns** through the gateway API with admin-role + MFA and audit entries.
9. **Secrets:** gateway keys in the secret manager, separate test/live, live keys unavailable to dev and CI.

---

## 9. Privacy and compliance considerations (for legal review)

- The app stores a persistent random `session_id` (localStorage) and behavioural events (30-day TTL) — this is personal-data processing under GDPR and India's DPDP Act 2023 once linked to a user or device. Needs a privacy notice, a consent mechanism for non-essential tracking, and deletion/export paths (`DELETE /me`, TTL already helps).
- Account data: email, name, size and style preferences. Document retention; encrypt at rest (Atlas default) and restrict access.
- Consumer-protection: remove the fabricated claims (H-08) and publish real shipping/returns terms before accepting orders.
- Accessibility obligations may apply to commercial storefronts depending on market.
These are flags for counsel, not advice.

---

## 10. Logging, monitoring and incident response

Nothing exists today (H-10). Minimum for launch: structured JSON logs with request IDs (no PII/secrets/tokens), auth events (login success/failure, password change, role change), admin actions, payment/webhook outcomes, rate-limit hits; alerts on 5xx rate, login-failure spikes, webhook failures, inventory anomalies, and cost spikes on AI endpoints; documented runbooks (secret rotation, account takeover, data restore); error tracking on web and API.

---

## 11. Prioritised remediation

| Pri | Items |
|---|---|
| **P0** | SEC-01 default secret; SEC-08 `is_active` on every request; SEC-11 verify bcrypt/passlib; SEC-13 role model foundation; `users.email` unique index (H-02) |
| **P1** | SEC-06 rate limits; SEC-07 verification/reset/revocation; SEC-09 cookie sessions; SEC-14 trust boundary for events; SEC-15 AI endpoint quotas; SEC-17 bounds; SEC-19 upload/fetch hardening; SEC-21 headers/CSP; SEC-02/03 secret hygiene + scanning; dependency audit |
| **P2** | SEC-05, SEC-10, SEC-22, SEC-24, SEC-20 |
| **P3** | SEC-12, SEC-16, SEC-23, SEC-25 |

## 12. Pre-launch security gate (acceptance criteria)

- [ ] App refuses to start in non-dev with default/weak secret (tested).
- [ ] `users.email` unique index exists; duplicate-signup race test passes.
- [ ] Deactivated or version-bumped user token rejected on next request (test).
- [ ] Login/signup/AI endpoints rate-limited; 429 returned with `Retry-After` (test + load test).
- [ ] Admin endpoints return 403 for customers; ownership tests for cart/orders.
- [ ] No endpoint accepts client-supplied prices; checkout recomputes server-side (test).
- [ ] Payment webhook rejects bad signature and replays; duplicate event is a no-op (test).
- [ ] CSP/HSTS/headers verified with an external scanner; no inline-script violations.
- [ ] `gitleaks`, `pip-audit`, `npm audit`/`osv-scanner` pass in CI with zero high/critical.
- [ ] Penetration test or at least OWASP ASVS L1 checklist completed against staging.
- [ ] Atlas: least-privilege user, IP allow-list/private link, backups restore-tested.
