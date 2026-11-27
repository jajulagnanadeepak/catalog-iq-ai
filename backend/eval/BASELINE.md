# Phase 1 — Search-Quality Baseline (WS-F)

**Status:** Baseline v0 is recorded: a manual test by the project owner on 2026-11-27, run locally against the real 105,542-product catalogue and the existing FAISS index. The automated baseline (v1) is next (§5).
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

## 3. Proposed improvements (for approval; not implemented)

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
| S10 | **New finding, for approval (not part of the approved S1–S7).** Queries containing best/recommend/suggest/popular take the `recommendation` path. `RecommendationEngine.recommend()` reads `product["name"]` from the search-result wrapper, but the name is in `item["product"]["name"]`, so **every item is skipped and 0 products are returned**. Found by reading the code; the eval's `recommendation` group (r1–r6) measures it. Proposed fix: send this intent through the v2 reranker (v2 only). | Recommendation queries | `routes/semantic_search.py` (v2 branch only) |
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

## 5. Exact implementation plan for S1–S7 (approved; starts only after the v1 baseline report)

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

## 6. Next steps (in order)

1. ✅ **WS-F automated harness built** (`backend/eval/`, 174 queries, 21 passing harness tests). ⏳ **The v1 baseline run needs your machine:** `python -m eval.run_eval --label v1` (see `eval/README.md`).
2. With your approval, implement S1–S7 behind `SEARCH_RERANK_VERSION=v2` (default `v1`).
3. You run the harness locally against the real catalogue for v1 and v2 → compare the reports → you decide whether to switch the default.
