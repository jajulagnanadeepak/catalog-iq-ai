# Phase 1 — Search-Quality Baseline (WS-F)

**Status (updated 2026-11-28):** Baseline v0 (manual, §1) and the automated v1 baseline are recorded. S1, S2, a trench-coat vocabulary correction, S4, S3-lite and the S5 hard tier are implemented behind feature flags that all default to off, and are evaluated in §7. S6–S9 are not implemented. S10 (recommendation path returning 0 results) is fixed and merged into `main` (§7.5); its result quality has not been evaluated against the live backend. None of this has been deployed or enabled by default; it is not production-ready.
**Code under test:** `feat/p1-backend-foundation` (WS-A). WS-A does not change search behaviour, so this is also the baseline for `main@5d7ba72`.
**Endpoint:** `POST /api/semantic-search` (FAISS retrieves 100 candidates → `SemanticReranker`).
**Constraint:** the catalogue and the FAISS index are not modified, deleted or rebuilt. Every proposed change is query-time code only, behind a flag, and measured against this baseline.

---

## 1. Baseline v0: manual results (as reported by the project owner)

| # | Query | Intent detected | Results | Outcome | Owner's finding |
|---|---|---|---|---|---|
| Q1 | black casual dress for women | `occasion_search` (0.9) | 100 candidates; top results New York tunic dress, Solo dress; also a jumpsuit and a blouse | ⚠️ Partial | Product-type relevance is not strict enough |
| Q2 | summer floral dress | `seasonal_search` (0.9) | **3 results for top_k=5**: a children's dress, a sweater, a blouse | ❌ Poor | Category, audience and floral attribute insufficiently constrained |
| Q3 | formal trousers for office wear | — | 5 relevant trousers (tailored, slacks) | ✅ Good | Men's and women's mixed; acceptable without a gender term |
| Q4 | comfortable running shoes | — | 5 relevant sneakers or trainers | ✅ Good | Comfort not reflected explicitly in the ranking |
| Q5 | gaming laptop with RTX graphics | — | Laptop case, backpack, unrelated clothing and footwear; scores much lower than for fashion queries | ❌ Poor | Out-of-catalogue query not rejected; low-relevance results not suppressed |

**Working, per the owner:** the API, semantic retrieval, FAISS candidates, intent detection, ranking, score breakdown output, explanations, and fashion and footwear retrieval.
**Needs improvement, per the owner:** strict product-type matching, category constraints, attribute extraction (colour, floral, comfort), audience filtering, score calibration, out-of-catalogue detection, rejecting low-confidence results, and misleading explanations on unrelated products.

---

## 2. Root-cause analysis (code and data, read-only)

| Finding | Root cause | Evidence |
|---|---|---|
| **Q1 and Q2: dresses mixed with other types** | The query parser has **no dress category**. Its categories are outerwear, tops, trousers, footwear, bags, swimwear and knitwear. "dress", "jumpsuit" and "skirt" never set `category`, so the hard category filter never applies. | `services/query_parser.py:40-69`; `services/semantic_reranker.py:69-80` |
| **Q2: 3 results for top_k=5** | With no category detected, the diversity cap applies: `max_per_category = max(1, int(5 × 0.35)) = 1`. That allows **one product per inferred category**, and the candidates spanned only about three inferred categories. There is no backfill when the cap leaves fewer than `top_k`. | `services/semantic_reranker.py:165-177, 1015-1061` |
| Q1 and Q2: categories inferred for products | `_infer_product_category` has no dress or full-body category and falls back to `None`. Every dress, jumpsuit and skirt therefore shares the single `"unknown"` diversity bucket, so **at most one** of them survives the cap. That matches Q2 exactly: one dress (unknown) + sweater (knitwear) + blouse (tops) = 3. In Q1 a second dress-like item probably came through another bucket (for example a tunic classified as a top). This is inferred from the code, not reproduced here. | `semantic_reranker.py:581-783` (returns nightwear, footwear, bags, outerwear, trousers, knitwear, tops, else `None`); `:1036-1041` |
| **Q2: a children's dress for an adult query** | `catalog_products` does not store the audience: the import drops `index_group_name`. Audience can only be guessed from department and section text, which catches all 34,711 children's items but also wrongly flags 626 adult items. | `database/import_hm_catalog.py:57-68`; `articles.csv` analysis |
| **Q2: "floral" not used** | There is no pattern attribute in the parser. The catalogue has no floral flag either: `graphical_appearance_name` is not imported, and even in the CSV it is generic ("All over pattern" 17,165). Only **198** descriptions mention floral or flower. | `query_parser.py`; `articles.csv` |
| Q4: "comfortable" not used | No comfort attribute exists in the data. Only a soft keyword or description boost is possible; anything stronger would mean inventing data. | `articles.csv` columns |
| **Q5: out-of-catalogue query not rejected** | No catalogue-scope check and no minimum-relevance threshold; the reranker always returns up to `top_k` | `routes/semantic_search.py:72-86`; `semantic_reranker.py` |
| Scores not calibrated | The weights add up to 1.25 (0.40 + 0.15 + 0.35 + 0.10 + 0.10 + 0.15), and the semantic score is `1/(1+L2)`, an unbounded transform with no threshold | `semantic_reranker.py:12-17, 117-128, 319-327` |
| Misleading explanations | Reasons are generated for every returned item, including unrelated ones | `semantic_reranker.py:1089+` |
| Rupee budgets ("under ₹3,000") not parsed | The budget regex only allows `$`, and there are no prices in the H&M data anyway | `query_parser.py:79-86` |

**Why Q3 and Q4 work:** "trousers" and "shoes" are parser keywords, so the hard category filter applies and the diversity cap is skipped.

---

## 3. Proposed improvements

> **Implementation status:** S1, S2 and S4 are implemented as proposed, except that S4 identifies children's products by `section` (100% equivalent to `index_group_name`, see §7) instead of waiting for WS-C. S3 is implemented in a reduced form ("S3-lite": pattern boost and `navy` only). S5 is implemented as a vocabulary-based hard tier without a relevance threshold. S6, S7, S8, S9 and S10 are **not** implemented. Each implemented change has its own flag instead of a single `v2` switch. Details and measurements are in §7.

All of these are query-time changes. **No catalogue or FAISS writes, and no re-embedding.** They live behind the setting `SEARCH_RERANK_VERSION` (`v1` is the default and the current behaviour; `v2` is the new one). `v1` stays the default until the automated eval shows `v2` has no regressions and you approve the switch.

| ID | Change | Fixes | Files |
|---|---|---|---|
| S1 | Add `dresses`, `jumpsuits`, `skirts`, `underwear`, `nightwear`, `accessories` (and more) to the parser and to `_infer_product_category`, driven by the catalogue's own `product_type` values. Most specific match wins ("bikini top" → swimwear, not tops). | Q1, Q2, AI-08 | `services/query_parser.py`, `services/semantic_reranker.py`, new `services/catalog_vocabulary.py` |
| S2 | Diversity cap: cap of at least 2, then **backfill** to `top_k` from the remaining ranked candidates | Q2 count | `services/semantic_reranker.py` |
| S3 | Pattern and attribute terms (floral, striped, denim, checked, lace, …) and comfort terms (comfortable, soft, stretch, relaxed) as **soft boosts** on name and description text, without overstating them; colour matching is unchanged | Q2, Q4 | `services/query_parser.py`, `services/semantic_reranker.py` |
| S4 | Audience extraction (women, men, kids, girls, boys, baby). Adult or unspecified queries **downrank** children's items rather than exclude them. Interim signal: department and section text. Accurate signal: `index_group_name` added to the **new** `catalog_items` collection in WS-C (additive; `catalog_products` untouched). | Q2 | `services/query_parser.py`, `services/semantic_reranker.py` |
| S5 | Out-of-catalogue detection: (a) a vocabulary of what the catalogue actually carries, built from its product types and groups; (b) a list of unsupported domains (laptop, phone, headphones, TV, gaming, GPU/RTX, …); (c) a minimum-relevance threshold **calibrated on the eval set**, not guessed. The response gains additive fields `out_of_catalog: true` and a `message`, with `products: []`. | Q5 | new `services/catalog_scope.py`, `routes/semantic_search.py` |
| S6 | Score calibration: normalise the weights so they sum to 1. Ranking order is mathematically unchanged; only the displayed score values change. Report `relevance` on a 0–1 scale, and use it for S5's threshold. | Calibration | `services/semantic_reranker.py` |
| S7 | Explanations only state attributes that actually matched; nothing generic like "matches your search" for weak results | Misleading reasons | `services/semantic_reranker.py` |
| S8 | Budget regex accepts ₹ / Rs / INR. It only has an effect once prices exist (Phase 2). | Future | `services/query_parser.py` |
| S10 | **New finding, for approval (not part of the approved S1–S7).** Queries containing best/recommend/suggest/popular take the `recommendation` path. `RecommendationEngine.recommend()` reads `product["name"]` from the search-result wrapper, but the name is in `item["product"]["name"]`, so **every item is skipped and 0 products are returned**. Found by reading the code; the eval's `recommendation` group (r1–r6) measures it. Proposed fix: send this intent through the v2 reranker (v2 only). **Status: root cause fixed with a smaller change than proposed** — `RecommendationEngine.recommend()` now reads the nested `item["product"]` (flat products still accepted); merged into `main` (fix `252f1b2`, PR #3). The intent is **not** routed through the reranker; see §7.5. | Recommendation queries | `routes/semantic_search.py` (v2 branch only); as merged: `ai/recommendation_engine.py` |
| S9 | The frontend shows `out_of_catalog` and empty results honestly ("We don't carry gaming laptops") | Q5 UX | `src/routes/search.tsx`, `src/lib/api/services.ts` (WS-D) |

**Not in Phase 1** (Phase 3): hybrid BM25 retrieval, filters pushed into FAISS, a cross-encoder reranker, embedding-model changes, re-indexing, LLM query understanding.

**Tests to add:** `tests/test_query_parser_v2.py`, `tests/test_reranker_v2.py`, `tests/test_catalog_scope.py`. They use fixture products, need no DB, and include all five baseline queries as regression cases.

---

## 4. Acceptance criteria for v2 (measured on the eval set; v1 compared with v2 on the same run)

| Query | v1 (baseline) | v2 target |
|---|---|---|
| Q1 black casual dress for women | mixed types | ≥ 4 of the top 5 have `product_type` Dress; colour black where available; no children's items in the top 5 |
| Q2 summer floral dress | 3 results, mixed | **5 results**; ≥ 4 Dress; no children's items in the top 5; floral or print items ranked above solids where they exist |
| Q3 formal trousers for office wear | good | No regression: all 5 are trousers |
| Q4 comfortable running shoes | good | No regression: all 5 are footwear |
| Q5 gaming laptop with RTX graphics | irrelevant items | `out_of_catalog: true` and `products: []` |
| Whole eval set (150–300 queries) | measured in v1 | NDCG@10 ≥ v1; zero-result rate on **in-catalogue** queries ≤ v1; out-of-catalogue precision ≥ 0.9; p95 latency within +10 % of v1 |

---

## 5. Exact implementation plan for S1–S7 (original plan)

> This was the plan before implementation. What was actually built, and where it differs, is in §7.

**Query-time only: confirmed.** Every change below runs inside the request after FAISS retrieval, or in configuration. None of them:
- writes to MongoDB;
- reads or writes any collection other than the existing `catalog_products` lookup in `search.py`, which is unchanged;
- modifies, rebuilds or re-embeds `hm_products.index` / `hm_product_ids.pkl`;
- touches the import or embedding scripts.

The **v1 code path stays byte-for-byte as it is**: v2 lives in new modules.

| File | Change | New / modified |
|---|---|---|
| `backend/config.py` | `search_rerank_version: "v1" \| "v2"` (env `SEARCH_RERANK_VERSION`, default **`v1`**; any other value fails at startup) | modified (additive field) |
| `backend/services/catalog_vocabulary.py` | Static vocabulary: product type → category (S1), synonyms, pattern and comfort terms (S3), audience words (S4), unsupported-domain terms (S5). Plain constants taken from the catalog's own type values. | **new** |
| `backend/services/query_parser.py` | Add `extract_v2()` (S1, S3, S4). The existing `extract()` is untouched. | modified (additive method) |
| `backend/services/semantic_reranker_v2.py` | `SemanticRerankerV2(SemanticReranker)`: category inference covering every product type (S1); diversity cap ≥ 2 with backfill to `top_k` (S2); soft attribute boosts (S3); children's downranking for non-kids queries (S4); normalised weights and a 0–1 `relevance` (S6); explanations only for attributes that matched (S7) | **new** (v1 class unchanged) |
| `backend/services/catalog_scope.py` | Out-of-catalogue detection (S5): unsupported-domain terms + a catalogue-vocabulary check + a minimum-relevance threshold, **calibrated from the v1 report** | **new** |
| `backend/routes/semantic_search.py` | Pick the reranker from the setting. v2 adds response fields `rerank_version`, `out_of_catalog`, `message`. The v1 response is unchanged. | modified (branch) |
| `backend/.env.example`, `backend/README.md`, `eval/README.md` | Document the flag | docs |
| `backend/tests/test_query_parser_v2.py` | S1, S3, S4 extraction, including "bikini top" → swimwear and "dress" → dresses | **new** |
| `backend/tests/test_reranker_v2.py` | Fixture products reproduce Q1–Q4 (Q2 must return 5 results, ≥4 dresses, no children's items); backfill; scores in 0–1; reasons only for matched attributes | **new** |
| `backend/tests/test_catalog_scope.py` | Q5 and the 23 out-of-catalogue queries are rejected; in-catalogue look-alikes (laptop bag, phone case, watch, side table) are not | **new** |
| `backend/tests/test_semantic_search_versions.py` | Default is v1, with the response shape unchanged; v2 only when the flag is set; an invalid flag fails at startup | **new** |

**Option to measure, not assumed:** v2 may ask FAISS for more candidates than 100 (for example 300) so the category filter has enough to backfill. This is still a read-only query-time change. It goes in only if the eval shows a gain within the latency budget.

## 6. Next steps

1. ✅ WS-F automated harness built (`backend/eval/`, 174 queries).
2. ✅ v1 baseline run (`eval/reports/v1.*`). Run it against `http://127.0.0.1:8000`: on Windows, `localhost` first tries IPv6 and adds about 2 s to every request.
3. ✅ S1, S2, trench correction, S4, S3-lite and S5 hard tier implemented behind flags and evaluated (§7).
4. ⏳ Decide whether and when to enable the v2 flags outside development. This has not been decided, and the known issues in §7.5 should be considered first.
5. Deferred: S5b, S6–S9, and the Phase 3 retrieval work (§7.6). (S10 was originally deferred here; it is now fixed and merged, §7.5.)

## 7. Phase 1 results

All runs use the same 174-query set (`queries.jsonl`, sha256 `444f403e974d`), the real 105,542-product catalogue and the unchanged FAISS index (`hm_products.index`). The catalogue, MongoDB data, index and embeddings were not modified. Reports are in `eval/reports/`. The reports' `git_commit` field shows `c10ee67` for all runs because the S1–S5 code was not yet committed when they ran.

### 7.1 Metrics by stage

Each stage adds to the one before. NDCG, P@5 and fill rate are over in-catalogue queries. "Strong" is the mean NDCG@10 of the 70 queries with v1 NDCG@10 ≥ 0.8.

| Report | Configuration | NDCG@10 | P@5 | Fill rate | Zero-result rate | Children's items in non-kids top 5 | Kids-query NDCG | Strong | OOC correct | Targets |
|---|---|---|---|---|---|---|---|---|---|---|
| `v1` | v1 (current default) | 0.6217 | 0.6493 | 0.769 | 0.073 | 0.068 | 0.5575 | 0.9411 | 0.0 | 3/28 |
| `v2` | S1 + S2 | 0.8444 | 0.8333 | 0.960 | 0.040 | 0.057 | 0.9456 | 0.9462 | 0.0 | 3/28 |
| `v2-trench` | + trench correction | 0.8454 | 0.8360 | 0.960 | 0.040 | 0.055 | 0.9456 | 0.9483 | 0.0 | 3/28 |
| `v2-s4` | + S4 | 0.8714 | 0.8733 | 0.960 | 0.040 | 0.012 | 0.9456 | 0.9692 | 0.0 | 3/28 |
| `v2-s3` | + S3-lite | 0.8743 | 0.8760 | 0.960 | 0.040 | 0.012 | 0.9456 | 0.9692 | 0.0 | 4/28 |
| **`v2-s5`** | **+ S5 hard tier (all flags on)** | **0.8743** | **0.8760** | **0.960** | **0.040** | **0.012** | **0.9456** | **0.9692** | **1.0 (24/24)** | **28/28** |

Against v1, 95 of 150 in-catalogue queries improved and 1 is worse (p10 "beige trench coat", 0.8132 → 0.7979, from S4). S5 changed 0 of the 150 in-catalogue results. On a separate held-out set written for the S5 investigation, the classifier caught 22/24 unavailable products (92%) and flagged 0 of 36 in-catalogue look-alikes ("phone case", "laptop sleeve", "side table", …).

Each flag was verified to be isolated: with the newest flag off, a full eval run reproduced the previous stage with 0 per-query differences, and v1 (default settings) reproduced `v1.json` with 0 differences after every stage.

Latency: end-to-end p95 in single-client eval runs varied between about 105 and 360 ms for identical code, so it is dominated by machine load. Controlled, interleaved reranking-only benchmarks: S4 adds no measurable cost, S3-lite adds +4.2% at p95 (+0.5 ms), the S5 classifier costs about 0.15 ms at p95, and S5 skips FAISS for out-of-catalogue queries (median about 8 ms instead of about 215 ms). No load test has been done.

### 7.2 What was built

| Change | Implementation | Differences from the plan in §3/§5 |
|---|---|---|
| S1 | `services/catalog_vocabulary.py`: all 131 catalogue product types mapped to categories (product type first, then product group; section text never overrides). `services/query_parser_v2.py`: longest phrase / right-most head noun ("bikini top" → swimwear). Specific types rank first, then the rest of the broad category backfills. | — |
| S2 | `SemanticRerankerV2._apply_diversity_v2`: cap `max(2, int(top_k × 0.35))`, then backfill from skipped candidates in score order. | — |
| Trench correction | "trench" / "trench coat" match Coat **and** Jacket (the catalogue types 75 trench items as Jacket, 49 as Coat). | Added after the S1 evaluation |
| S4 | Soft −0.10 score penalty for children's products when the query does not mention children or an ambiguous audience ("teen", "daughter", …). Children's products are identified by 13 `section` values that hold exactly the 34,711 "Baby/Children" articles. Nothing is removed. | Uses `section` instead of `index_group_name`/WS-C |
| S3-lite | +0.25 × (share of requested patterns found in name/description) when the query names a pattern **and** S1 detects a category; `navy` → `dark blue` in colour matching. No penalty for non-matching products. | Material, full colour normalisation and occasion boosts were simulated and rejected (no meaningful gain or regressions) |
| S5 hard tier | `services/catalog_scope.py`: a query is out of catalogue only if S1 finds no category **and** no catalogue product-type or accessory phrase is present **and** an explicit unsupported-domain phrase is present (electronics, appliances, furniture, food/health, auto/tools, sport/music). Checked before FAISS; such queries return `products: []`, `out_of_catalog: true`, `ooc_reason: "unsupported_domain:<domain>"`. | No relevance threshold (S5b deferred); ambiguous words only as full phrases ("computer mouse", "cricket bat", "garden hose") |

### 7.3 Feature flags

All default to off, so the API behaves exactly as before (v1) unless they are set.

| Variable | Default | Effect |
|---|---|---|
| `SEARCH_RERANK_VERSION` | `v1` | `v1` or `v2` (S1 + S2 + trench correction). Any other value fails at startup |
| `SEARCH_V2_KIDS_DOWNRANK` | `false` | S4. v2 only |
| `SEARCH_V2_ATTRIBUTE_BOOST` | `false` | S3-lite. v2 only |
| `SEARCH_V2_OUT_OF_CATALOG` | `false` | S5 hard tier. v2 only |

The S3, S4 and S5 flags are independent of each other. v2 responses add `rerank_version: "v2"`; S5 responses for out-of-catalogue queries add `out_of_catalog` and `ooc_reason`. Normal in-catalogue responses get no other new fields.

### 7.4 Tests

`pytest tests` (no database, network or index needed): 380 passed. The existing safe tests listed in `backend/README.md`: 37 passed and 4 failed. The 4 failures are the known bcrypt/passlib issue in §7.5, not caused by this work. (Since fixed by WS-B, merged into `main`; see §7.5. After the WS-B and S10 merges, `pytest tests` on `main` `cc902e0`: 467 passed, and the 4 `test_auth.py` failures no longer occur.)

### 7.5 Known issues and limitations

| Issue | Severity | Notes |
|---|---|---|
| Recommendation intent returns 0 results | High → **fixed, merged into `main`** | Queries with best/recommend/suggest/popular take `RecommendationEngine.recommend()`, which reads the name from the wrong level of the search result (proposal S10). Affects 6 eval queries; pre-existing. **S10 fix merged into `main`** (fix `252f1b2`, PR #3, merge `cc902e0`): the engine now reads the nested `item["product"]` returned by `semantic_search()` and still accepts flat product dicts. 38 regression tests pass (`tests/test_recommendation_engine.py`), and all six S10 queries (r1–r6) return results through the route; Copilot's recommendation replies return results too. **Limitation: recommendation quality has not been evaluated against the live backend/database.** Results were validated only with test fixtures and in-memory fakes, so the r1–r6 metrics in §7.1 are unchanged until the eval is re-run. Results are in raw FAISS order (no reranker category filtering), and the route still ignores `top_k` for this intent |
| bcrypt 5.0.0 / passlib 1.7.4 incompatibility | High → **resolved, merged into `main`** | Signup and login failed in a fresh environment; 4 tests in `test_auth.py`. Pre-existing. **WS-B fix merged into `main`** (fix `daa4f19`, PR #2, merge `dbb95e5`); post-merge validation on `main` `cc902e0` passed (58 auth/password tests, 467 in `pytest tests`). Passlib removed, `bcrypt==5.0.0` kept and called directly (cost 12); existing bcrypt hashes still verify (login uses the legacy first-72-UTF-8-bytes behaviour); new signup passwords are limited to 72 UTF-8 bytes (HTTP 422); missing or malformed stored hashes give 401 instead of 500 |
| Copilot still uses v1 search | Medium | `ai/copilot.py` creates the v1 `SemanticReranker` |
| Gender inference substring defect | Medium | Inherited `_infer_gender` matches "men" inside "garment", so 79% of children's products are classed as men's. A simulated fix showed no quality gain; not fixed |
| Retrieval gaps | Medium | Floral blouses, leopard dresses and polka-dot dresses exist in the catalogue but are not among the 100 FAISS candidates (p4, p6, p7); "black formal shoes for office" (o1) returns sneakers; no comfort data (b4). Reranking cannot fix these (Phase 3) |
| Multi-colour queries are not deterministic across restarts | Medium | The inherited colour list is a Python `set` |
| S5 vocabulary is hand-written | Low | Unlisted products (e.g. kitchen knife sets, strollers) get normal results; some single words ("car", "phone", "bed") are listed; catalogue type names can protect real OOC queries ("smart watch"). All of these fail safe (normal results) |
| p10 below v1 | Low | −0.015 NDCG@10, from S4 |
| Eval tooling | Low | `compare.py` crashes on the Windows console unless `PYTHONIOENCODING=utf-8`; report `git_commit` does not flag uncommitted code |

### 7.6 Evaluation limitations

- The eval set has only 6 kids queries, 18 attribute queries and no ambiguous-audience queries.
- Labels come from the same catalogue fields as the S1 and S3 vocabularies, so gains on generated queries are partly expected by construction.
- The S4 and S5 held-out query sets were written during the investigations, not by an independent party; real-world recall is likely to be lower.
- All latency figures are single-client.

### 7.7 Deferred

- **S5b**: low-confidence flag based on retrieval distance (margin too thin; index-specific).
- **S6–S8**: score normalisation, explanations only for matched attributes, rupee budgets.
- **S9**: showing `out_of_catalog` and empty results in the frontend.
- **S10**: the recommendation-path fix. **Done:** the minimal fix is merged into `main` (§7.5). Still open: evaluating recommendation quality against the live backend, and optionally routing the intent through the reranker as originally proposed.
- **Phase 3**: retrieval improvements (hybrid keyword + vector retrieval, larger candidate pools, re-ranking models).
