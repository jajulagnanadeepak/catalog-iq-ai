# CatalogIQ AI — AI / ML Review

Commit audited: `5d7ba72`. Companion to [CATALOGIQ_AUDIT.md](CATALOGIQ_AUDIT.md) (IDs `C-/H-/M-/L-`); `AI-` IDs are specific to this review.

## 0. What this review can and cannot say

**Cannot say (no data/models/index were available, no network):** how relevant the search results are, how fast they are, how good the recommendations are, whether the 105,542-row index is complete or aligned with Mongo. **No relevance, latency or quality number appears anywhere in this document** — if you see one in a README or demo, it was not measured here.

**Can say:** what the code does, where its design puts quality or availability at risk, what is missing to measure and improve it, and which parts are good and should be kept.

Instruction honoured: *the 105,542-product catalog and the existing search pipeline are preserved.* Every recommendation below is additive or a bug fix; none replaces MongoDB, FAISS, Sentence-Transformers or Gemini.

---

## 1. Pipeline as implemented

```
OFFLINE (create_hm_embeddings.py)
  Mongo catalog_products (sorted by _id)
    → text = name · product_type · category · department · section · garment_group · colour · description   (space-joined)
    → SentenceTransformer("all-MiniLM-L6-v2").encode(batch 64)  → float32 [N, 384]
    → faiss.IndexFlatL2(384).add()  → hm_products.index        (+ hm_product_ids.pkl = [article_id,…] in the same order)

ONLINE (search.py → routes/semantic_search.py)
  query → IntentDetector (rules) ─┬─ "recommendation": semantic_search(top 20) → dedupe by name   (NO rerank)
                                  └─ otherwise: semantic_search(top 100)
                                        → SemanticReranker (hard category filter, weighted score, dedupe, diversity)
                                        → top_k (default 10, max 50)
  session_id → session_events aggregate → primary_category/confidence → small intent boost
```

Visual search is a separate pipeline (CLIP image→image, Mongo `products`, live image fetches) — see AI-06.

---

## 2. Findings

### 2.1 Embedding generation

| ID | Sev | Finding | Evidence | Recommended fix |
|---|---|---|---|---|
| AI-01 | Medium | **No record of model/index provenance.** Index and ID map are two loose files; nothing stores the model name, embedding text template, catalog snapshot hash or build time. If `catalog_products` changes, the FAISS row→`article_id` mapping silently drifts (the importer's `delete_many` + re-insert plus the sort by `_id` is the only guard). | `create_hm_embeddings.py:44-58,112-115`; `search.py:24-27` | Write a `manifest.json` next to the artefacts (model, dim, template version, row count, `sha256` of the ID list, built_at); check row count and a few sampled IDs at startup; fail readiness if they disagree. Rebuild is a pure function of the catalog. |
| AI-02 | Medium | **Single concatenated text with no field weighting.** Name, product type, section etc. are joined with spaces; long `description` dominates MiniLM's 256-token window and may truncate trailing fields; colour appears once. | `create_hm_embeddings.py:69-80` | Keep the model; A/B a structured template (e.g. `"{name}. {product_type}. Colour: {colour}. {department}, {section}. {description[:300]}"`) against the current one **using the evaluation set (AI-09)** — change only if metrics improve. |
| AI-03 | Low | **Language/domain fit.** MiniLM-L6 is English-only and general-purpose. Fine for H&M English metadata; queries in Hindi/other languages (your market) will degrade. | `create_hm_embeddings.py:11` | Don't swap now. Log language-detected queries and revisit with a multilingual model only if data shows demand. |
| AI-04 | Low | **Distance semantics.** README says "Cosine Similarity" but the index is `IndexFlatL2` and the reranker converts distance with `1/(1+d)` (`semantic_reranker.py:320-330`). For unit-length vectors L2 ranking equals cosine ranking; `all-MiniLM-L6-v2`'s pipeline normally ends with a Normalize layer, which would make this correct — but the code never asserts it. *(Unverified here: models not available.)* | `create_hm_embeddings.py:96-105` | Assert `abs(norm-1)<1e-3` on a sample at build time and document the equivalence; or build `IndexFlatIP` on normalised vectors. Fix README wording. |
| AI-05 | Low | **Legacy builder is stale.** `create_embeddings.py` reads a non-existent `Products` collection and writes `products.index` that nothing loads. | `create_embeddings.py:46,113` | Delete or mark deprecated (history preserves it). |

### 2.2 FAISS indexing and retrieval

- **Index type is appropriate for the size.** Exact `IndexFlatL2` over 105,542 × 384 float32 ≈ **162 MB** (computed from the dimensions; actual file not inspected). Exact search is simple and gives best recall; there is no evidence that ANN (HNSW/IVF) is needed. *Do not change before measuring p95 latency.*
- **H-07 (High) — synchronous inference on the event loop.** `model.encode` and `index.search` run inside `async def semantic_search` (`search.py:33-47`), blocking all other requests on that worker for the duration. *Fix:* run both in a threadpool (`anyio.to_thread.run_sync`) or a dedicated inference process; cache query embeddings (LRU on normalised query text).
- **C-01 — import-time loading** of the model and a **git-ignored** index file (`search.py:18-27`, `.gitignore:53-54,63-64`). *Fix:* load in `lifespan`, readiness probe, manifest check (AI-01).
- **M-04 — memory model:** every Uvicorn/Gunicorn worker loads its own copy of the index and model. Use one worker per container (scale horizontally) or `mmap` the index (`faiss.read_index(path, faiss.IO_FLAG_MMAP)`) to share pages.
- **No metadata filtering at retrieval** (see AI-07): FAISS returns pure vector neighbours; any constraint (category, colour, stock, price) must be applied after retrieval or via `IDSelector`/partitioned indexes.
- **Mongo join:** `find({"_id": {"$in": article_ids}})` then restores FAISS order (`search.py:63-103`) — correct, and results lacking a Mongo document are skipped silently (no metric on how often that happens).

### 2.3 Semantic search relevance

**AI-07 (High, = H-05) — constraints are applied after retrieval, so recall collapses for constrained queries.** `semantic_search(query, top_k=100)` returns the 100 nearest neighbours of the *whole* query; the reranker then **hard-filters** by the parsed category (`semantic_reranker.py:71-80`). For "black top for women" the 100 neighbours may contain few true tops, and the answer set is whatever survives. Same for colour/gender signals, which only influence scores. *Fix:* over-fetch adaptively (e.g. 300–500) when a category/colour is detected, or build filtered search with a FAISS `IDSelectorBatch` of article IDs allowed by Mongo metadata; log `retrieved_candidates` vs surviving count (the endpoint already returns `retrieved_candidates`).

**AI-08 (Medium) — query parsing defects, verified by reading `services/query_parser.py`:**
1. `COLORS` is a Python `set` iterated with first-match (`:4-8, :79-86`); with two colours in a query ("black and white shirt") the winner depends on hash order, which changes **between processes** (string hash randomisation) — non-deterministic behaviour. Use an ordered structure and return all colours.
2. Category dictionary is first-match in insertion order (`:40-69`): `tops` precedes `swimwear`, so "bikini **top**" resolves to `tops`; the reranker then hard-filters out swimwear products (swimwear is inferred first for them, `semantic_reranker.py:582+`), so the user's intended results are *excluded*. Likewise "knit top" → tops, "sweater jacket" → outerwear.
3. Only seven categories are known; H&M's large dress, skirt, underwear, nightwear, accessories, socks groups have no parser category (the reranker infers some, the parser doesn't), so those queries bypass the category hard-filter and rely on vector similarity alone.
*Fix:* multi-label parse, longest-match-first, shared taxonomy module (M-02), regression tests built from real failing queries.

**H-05b — scoring weights are not normalised:** 0.40 + 0.15 + 0.35 + 0.10 (`self.weights`) plus literal 0.10 (occasion) and 0.15 (query-match) = **1.25** (`semantic_reranker.py:12-17, 117-128`). Scores are displayed as `score` (rounded) and used for ordering only, but any future threshold ("show only > 0.6") or blending with other signals will misbehave. Normalise to sum 1 and re-tune on the evaluation set.

**AI-09 (High) — there is no relevance evaluation.** The existing "relevance" tests compare two hand-made products on a single feature (`test_semantic_reranker_relevance.py`) and `check_search_relevance.py` prints top-10 for three queries for a human to read. There is no labelled query set, no metric, no regression gate. Every tuning change in git history ("Improve product recommendation relevance" ×2, "Fix product type filtering", the `.before_relevance_fix` backup) was therefore judged by eye. *Fix (before any further tuning):*
- Build a golden set of **150–300 real-style queries** (colour, category, occasion, budget, gender, long-tail phrasing, typos) with graded relevance labels for the top-20 candidates (2 reviewers; resolve disagreements).
- Track **Recall@100** (retrieval), **NDCG@10**, **MRR**, **precision@5**, zero-result rate, category-purity, and duplicate rate. Run in CI on a small fixture index plus nightly on the full index.
- Only then tune weights/templates.

**AI-10 (Medium) — dedupe removes colour variants.** `_apply_deduplication` keeps one product per `(name, product_type)` (`semantic_reranker.py:247-315`). That's good for diversity, but hides alternative colours for the same style and may hide the *requested* colour if a different variant outscored it. Prefer grouping variants under one result with a colour selector (needs the canonical catalog, C-02).

### 2.4 Intent detection

- **M-01 (Medium)** — substring tests on the raw query (`ai/intent_detector.py:41-135`): `"rain" in "training"`, `"wear" in "swimwear"/"underwear"`, `"pair" in "repair"`, `"best" in "bestseller"`, `"gym"`; first match wins, order is budget → visual → recommendation → occasion → seasonal → styling. *Fix:* tokenise and match on word boundaries; allow multiple intents with scores.
- **AI-11 (Medium) — the "recommendation" intent bypasses the reranker.** When the query contains *recommend / suggest / best / popular*, both `/semantic-search` and the copilot call `RecommendationEngine.recommend`, which is raw FAISS top-20 → dedupe by name, **no category filter, no session intent, no attributes** (`routes/semantic_search.py:54-66`, `ai/copilot.py:122-140`, `ai/recommendation_engine.py:21-63`). "best black jeans" therefore returns worse-constrained results than "black jeans". Also this branch ignores `top_k`. *Fix:* treat these words as a *modifier* on the normal pipeline, not a different pipeline.
- **AI-12 (Low) — confidences are constants** (0.95, 0.94, 0.92 …) returned as `confidence`; they are not probabilities. Rename to `rule_strength` or drop from the UI.
- **Routing gaps:** detected intents `styling`, `seasonal_search`, `visual_search` return `tool` values the copilot never dispatches (`ai/copilot.py` handles only budget/recommendation, everything else → semantic search), so "what should I wear to a monsoon wedding" is answered by a plain product search.
- Two intent systems exist (`ai/intent_detector.py`, used by search/copilot; `services/intent_service.py`, used by `POST /api/intent`) with different labels and an unanchored budget regex (`intent_service.py:24`).

### 2.5 Product ranking, filtering, personalisation

- **AI-13 (High) — personalisation is effectively inert for the real catalog.** Session intent categories come from the `category` the frontend sends with each event (`tracking.ts:26`) — for H&M items that is `product_group_name` (e.g. "Garment Upper body"). `TaxonomyService.category_match_score` only recognises seven canonical names (outerwear, tops, trousers, footwear, bags, swimwear, knitwear) and returns 0 otherwise (`taxonomy_service.py:210-223`), so `intent_score` is 0 for catalog products; the `/recommend` endpoint, which does use session intent, only ever sees the 12 demo products and the frontend never sends `session_id` to it (`services.ts:391`). *Fix:* map H&M `product_group_name`/`product_type` to the canonical taxonomy at import time (store `taxonomy_category` on the canonical catalog item) and log the same key from the frontend.
- **Price/stock filters cannot work** on H&M rows (no price/stock fields; C-03). The frontend already treats missing price as "unknown" (`services.ts:296-308`).
- **Diversity cap** (`max_category_ratio=0.35`) is skipped when a category was parsed (`semantic_reranker.py:172-182`) — sensible.
- **Hard-coded heuristics** (occasion keywords, attribute scores, 1,313-line reranker) are readable but unprovable without AI-09; they should become data-driven where evidence shows value.

### 2.6 Recommendation quality

- `GET /recommend` (the dashboard widget) scores the **first 100 in-stock documents of the 12-item demo collection** (`recommendation_service.py:45`) — i.e. the same 12 products for everyone, in insertion order. It is a deterministic keyword/rating scorer with an explanation string, not a learned recommender, and contains no collaborative signal.
- `ai/recommendation_engine.py` defines the class twice (`:6`, `:15`), imports an unused `random`, and ignores `session_intent`.
- "Complete the look" and "Explainable AI" are claimed in the README. Explanations are templated from matched attributes (honest and fine), but the frontend's *fallback* explanations are fabricated (C-05).
- Recommended roadmap for quality: (1) fix data and plumbing; (2) content-based "similar items" via FAISS neighbours of the viewed item (cheap, uses existing index); (3) co-view/co-cart from `session_events` once real volume exists; (4) evaluate offline (hit-rate@k on held-out sessions) before shipping any learned model.

### 2.7 Gemini integration

**AI-14 (High, = H-06) — Gemini is absent.** The only reference is `README.md:54`. There is no SDK in `requirements.txt`, no key in `config.py`/`.env.example`, no client code, and `ai/copilot.py` generates text with f-strings. Before building it, decide its role (owner decision):
1. *Query understanding* (structured extraction of category/colour/occasion/budget/gender → feeds the existing retrieval + filters). Highest value, lowest risk, easy to evaluate.
2. *Grounded answer generation* over retrieved products ("why these three"), with citations to product IDs and **no invented attributes** (the codebase already values this: `recommendation_engine` comments forbid fabricating prices/ratings).
3. *Conversation memory* via `conversation_id` and a bounded message window.
Production requirements for any LLM call: key in secret manager, request timeout (≤8 s), retries with jitter, circuit breaker, **deterministic fallback to the current rule-based path**, token/cost budget and per-user quota, prompt-injection hygiene (treat product text and user text as data; never let model output choose DB queries directly), output schema validation, PII-free logging, and an offline eval of answer faithfulness. Gemini must **never** be on the critical path for plain search.

### 2.8 Visual search reliability

- **C-07 (Critical)** — per request: up to 100 serial HTTP fetches + 100 CLIP forward passes on the event loop, no caching, only the first 100 docs of the 12-item collection (`routes/visual_search.py:25-30, 91-130`). Reliability depends on third-party image hosts (Unsplash links already needed manual repair: `update_product_images.py`).
- Return value has `"detected": []` (`:168`); the frontend therefore shows nothing — unless the call fails, in which case it **fabricates** "Apparel / Fashion / Pattern match" (`services.ts:706`). Remove the fabrication.
- *Fix (keeps CLIP):* offline job embeds every catalog image once → separate FAISS index (`512-d`) + manifest; request path = one query embedding in a threadpool + one index search + Mongo join; add pixel cap (`Image.MAX_IMAGE_PIXELS`), content-type + magic-number validation (already good), rate limit; fallback = text search on the nearest category. H&M rows need real images first (C-03).
- CLIP model download (`from_pretrained`) happens lazily on first request (`lru_cache`), causing a long cold request and a network dependency in production — pre-download into the image.

### 2.9 AI response quality and latency

- Responses from copilot are templated sentences ("I found 5 products that best match your request."); quality ≈ the underlying search quality.
- **Latency is unmeasured.** Components on the request path: query encode (CPU), flat FAISS search over 105,542 vectors, one Mongo `$in`, Python reranking of ≤100 items with many string operations, plus (for budget intents) a live FX HTTP call (`exchange_rate_service.py:13`, no cache, M-06). Add per-stage timings (encode / faiss / mongo / rerank / total) to logs and metrics *first*; set SLOs from data (suggested starting targets to validate, not claims: p95 search < 500 ms, p95 copilot rule-path < 800 ms, visual search < 2 s).
- Cold start: SentenceTransformer + index + (lazily) CLIP load; readiness must wait for them.

---

## 3. Preserve / change summary

| Keep | Change (additive) |
|---|---|
| MiniLM + `IndexFlatL2` + 105,542-row catalog source | Manifest, readiness, threadpool, query-embedding cache (AI-01, H-07) |
| Reranker architecture (semantic + keyword + attribute + intent + diversity + reasons) | Normalise weights, fix parser (AI-08), pass recommendation intent through it (AI-11) |
| Session-event model with TTL | Taxonomy mapping at import so personalisation works on the real catalog (AI-13) |
| CLIP for visual search | Offline image index (C-07) |
| Deterministic, explainable `reason` strings | Optional Gemini layer with deterministic fallback (AI-14) |
| — | **Evaluation harness first (AI-09)** |

## 4. Acceptance criteria for the AI workstream (referenced by Roadmap Phase 4)

1. Golden query set ≥150 queries committed; metrics script reproducible; baseline recorded **before** any tuning.
2. Retrieval Recall@100 and NDCG@10 non-regressing vs. baseline on CI; any change that lowers them is blocked.
3. Constrained queries (category/colour/gender) return ≥ the baseline number of valid results at the same `top_k`; "bikini top" returns swimwear.
4. Index manifest verified at startup; readiness fails on mismatch.
5. Search p95 and error rate visible on a dashboard; semantic-search handler no longer blocks the event loop (load test with 50 concurrent users shows other endpoints stay responsive).
6. Visual search p95 < target with a catalog-wide image index; no network fetch of catalog images at request time.
7. If Gemini is enabled: faithfulness eval ≥ agreed threshold, fallback path proven by killing the Gemini key in staging, cost cap enforced.
