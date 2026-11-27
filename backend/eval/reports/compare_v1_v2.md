# Search quality: v1 vs v2 (S1 + S2)

- **v1:** `reports/v1.json`, the owner's run of 2026-11-27 against `http://127.0.0.1:8000`, code `c10ee67`.
- **v2:** `reports/v2.json`, run against `http://127.0.0.1:8001` with `SEARCH_RERANK_VERSION=v2`. The code was uncommitted on top of `c10ee67`; the report's `git_commit` field shows only the base commit.
- **Data:** the same 174-query set (sha256 `444f403e974d`), the same catalogue (105,542 products) and the same FAISS index. Nothing was modified.
- **v1 check:** the new code with the default flag (v1) was evaluated again. All 174 queries returned results identical to `v1.json`, with 0 per-query differences.

## Summary

| Metric | v1 | v2 | Δ |
|---|---|---|---|
| NDCG@10 (in-catalogue) | 0.6217 | **0.8444** | +0.2227 |
| P@5 | 0.6493 | **0.8333** | +0.184 |
| P@10 | 0.546 | 0.7867 | +0.2407 |
| MRR | 0.7889 | 0.9079 | +0.119 |
| Fill rate | 0.7693 | **0.96** | +0.1907 |
| Zero-result rate (in-catalogue) | 0.0733 | **0.04** | −0.0333 |
| Children's items in top 5 (non-kids queries) | 0.0677 | 0.0565 | −0.0112 |
| Out-of-catalogue correct | 0.0 | 0.0 | 0 (S5 not implemented) |
| Latency p95, end to end (ms) | 112.0 | 173.9 | +61.9 (within noise, see below) |
| Targets passed | 3 / 28 | 3 / 28 | 0 |

Per query: **77 improved, 69 unchanged, 4 worse** (of 150 in-catalogue queries).

## By group (NDCG@10)

| Group | v1 | v2 | Δ |
|---|---|---|---|
| attribute | 0.6268 | 0.8202 | +0.1934 |
| baseline | 0.5326 | 0.6893 | +0.1567 |
| generated | 0.6586 | 0.8953 | +0.2367 |
| kids | 0.5575 | 0.9456 | +0.3881 |
| occasion | 0.6276 | 0.8510 | +0.2234 |
| synonym | 0.7005 | 0.8755 | +0.1750 |
| recommendation | 0.0 | 0.0 | 0 (S10 not implemented) |
| out_of_catalog (correct rate) | 0.0 | 0.0 | 0 (S5 not implemented) |

**Bias note:** the S1 vocabulary and the eval labels both come from the catalogue's product types, so gains in the `generated` group are partly expected by construction. The hand-written groups (attribute, occasion, synonym, kids, baseline) improved by +0.16 to +0.39.

### By v1 parser category (the code path each query took in v1)

| category | n | NDCG v1 | NDCG v2 | Δ | P@5 v1 | P@5 v2 | mean results v1 → v2 | queries worse |
|---|---|---|---|---|---|---|---|---|
| (none) | 44 | 0.393 | 0.821 | +0.428 | 0.491 | 0.818 | 5.2 → 9.5 | 0 |
| tops | 32 | 0.556 | 0.877 | +0.321 | 0.569 | 0.875 | 7.6 → 10.0 | 2 |
| trousers | 19 | 0.644 | 0.824 | +0.181 | 0.621 | 0.768 | 8.4 → 9.5 | 0 |
| footwear | 19 | 0.803 | 0.812 | +0.010 | 0.821 | 0.821 | 9.5 → 9.5 | 0 |
| outerwear | 17 | 0.826 | 0.869 | +0.043 | 0.812 | 0.859 | 9.4 → 9.4 | 1 |
| knitwear | 10 | 0.905 | 0.905 | +0.000 | 0.860 | 0.860 | 10.0 → 10.0 | 0 |
| bags | 5 | 0.759 | 0.734 | -0.024 | 0.760 | 0.720 | 8.0 → 8.0 | 1 |
| swimwear | 4 | 0.942 | 0.971 | +0.029 | 1.000 | 1.000 | 10.0 → 10.0 | 0 |

### By v2 parser category

| category | n | NDCG v1 | NDCG v2 | Δ | P@5 v1 | P@5 v2 | mean results v1 → v2 | queries worse |
|---|---|---|---|---|---|---|---|---|
| tops | 28 | 0.652 | 0.868 | +0.215 | 0.671 | 0.871 | 8.8 → 10.0 | 2 |
| footwear | 20 | 0.781 | 0.816 | +0.034 | 0.800 | 0.820 | 9.4 → 9.5 | 0 |
| trousers | 19 | 0.644 | 0.824 | +0.181 | 0.621 | 0.768 | 8.4 → 9.5 | 0 |
| outerwear | 17 | 0.826 | 0.869 | +0.043 | 0.812 | 0.859 | 9.4 → 9.4 | 1 |
| dresses | 12 | 0.385 | 0.773 | +0.387 | 0.583 | 0.900 | 5.7 → 9.2 | 0 |
| knitwear | 11 | 0.866 | 0.868 | +0.002 | 0.818 | 0.800 | 10.0 → 10.0 | 0 |
| accessories | 10 | 0.439 | 0.878 | +0.439 | 0.520 | 0.820 | 3.4 → 10.0 | 0 |
| swimwear | 10 | 0.379 | 0.953 | +0.575 | 0.400 | 0.940 | 4.4 → 10.0 | 0 |
| hoodies | 6 | 0.333 | 0.726 | +0.393 | 0.367 | 0.667 | 6.0 → 8.3 | 0 |
| bags | 5 | 0.759 | 0.734 | -0.024 | 0.760 | 0.720 | 8.0 → 8.0 | 1 |
| skirts | 4 | 0.386 | 0.913 | +0.527 | 0.400 | 0.800 | 3.8 → 10.0 | 0 |
| jumpsuits | 4 | 0.402 | 0.910 | +0.508 | 0.450 | 0.850 | 7.8 → 10.0 | 0 |
| (none) | 2 | 0.438 | 0.583 | +0.145 | 0.600 | 0.800 | 8.0 → 10.0 | 0 |
| nightwear | 2 | 0.469 | 1.000 | +0.531 | 0.600 | 1.000 | 3.0 → 10.0 | 0 |

### Previously strong queries (v1 NDCG@10 ≥ 0.8)

| category | n | NDCG v1 | NDCG v2 | Δ | P@5 v1 | P@5 v2 | mean results v1 → v2 | queries worse |
|---|---|---|---|---|---|---|---|---|
| strong | 70 | 0.941 | 0.946 | +0.005 | 0.929 | 0.929 | 10.0 → 10.0 | 4 |

### Every in-catalogue query whose NDCG@10 dropped

| id | group | query | NDCG v1 → v2 | v1 top 5 | v2 top 5 |
|---|---|---|---|---|---|
| p10 | attribute | beige trench coat | 0.813 → 0.665 (-0.148) | Coat / Beige; Coat / Mole; Jacket / Beige; Coat / Beige; Jacket / Beige | Coat / Beige; Coat / Mole; Coat / Beige; Coat / Mole; Coat / Beige [kids] |
| g146 | generated | pink bag | 0.872 → 0.750 (-0.122) | Bag / Pink; Bag / Pink; Bag / Pink; Bag / Pink [kids]; Bag / Pink | Bag / Pink; Bag / Pink [kids]; Bag / Pink; Bag / Pink; Bag / Pink [kids] |
| g86 | generated | green t-shirt | 0.838 → 0.730 (-0.109) | T-shirt / Green; T-shirt / Green; T-shirt / Khaki green; T-shirt / Green [kids]; T-shirt / Green | T-shirt / Green [kids]; T-shirt / Green; T-shirt / Green; T-shirt / Khaki green; T-shirt / Green [kids] |
| g88 | generated | blue t-shirt | 0.962 → 0.922 (-0.040) | T-shirt / Blue; T-shirt / Blue; T-shirt / Blue; T-shirt / Blue; T-shirt / Blue | T-shirt / Blue; T-shirt / Blue; T-shirt / Blue; T-shirt / Blue; T-shirt / Blue |

### Kids group

| id | query | NDCG v1 → v2 | results v1 → v2 | kids@5 v1 → v2 |
|---|---|---|---|---|
| k1 | girls party dress | 0.469 → 1.000 | 6 → 10 | 5 → 5 |
| k2 | baby bodysuit | 0.469 → 1.000 | 3 → 10 | 3 → 5 |
| k3 | sneakers for boys | 1.000 → 1.000 | 10 → 10 | 5 → 5 |
| k4 | kids raincoat | 0.469 → 0.759 | 6 → 10 | 5 → 5 |
| k5 | children's pyjamas | 0.469 → 1.000 | 3 → 10 | 3 → 5 |
| k6 | winter hat for kids | 0.469 → 0.915 | 6 → 10 | 5 → 5 |

Non-kids queries with ≥1 children's item in top 5: v1 28 / v2 25 (of 144)

### Owner baseline Q1–Q5

| id | ver | n | NDCG@10 | type@5 | kids@5 | targets | top 5 |
|---|---|---|---|---|---|---|---|
| b1 | v1 | 6 | 0.5638 | 4 | 0 | ✅ | Dress / Black; Dress / Black; Dress / Black; Dress / Black; Trousers / Black |
| b1 | v2 | 10 | 1.0 | 5 | 0 | ✅ | Dress / Black; Dress / Black; Dress / Black; Dress / Black; Dress / Black |
| b2 | v1 | 5 | 0.1381 | 3 | 3 | ❌ kids_at5_max, type_at5_min | Dress / Green [kids]; Dress / Yellow; Dress / Green; Sweater / White [kids]; Blouse / Turquoise [kids] |
| b2 | v2 | 10 | 0.3286 | 5 | 1 | ❌ attribute_at5_min, kids_at5_max | Dress / Green [kids]; Dress / Yellow; Dress / Green; Dress / Mole; Dress / Blue |
| b3 | v1 | 10 | 1.0 | 5 | 0 | ✅ | Trousers / Grey; Trousers / Blue; Trousers / Khaki green; Trousers / Blue; Trousers / Beige |
| b3 | v2 | 10 | 1.0 | 5 | 0 | ✅ | Trousers / Grey; Trousers / Blue; Trousers / Khaki green; Trousers / Blue; Trousers / Beige |
| b4 | v1 | 10 | 0.4286 | 5 | 0 | ✅ | Sneakers / White; Sneakers / Khaki green; Sneakers / Mole; Sneakers / Unknown; Sneakers / Mole |
| b4 | v2 | 10 | 0.4286 | 5 | 0 | ✅ | Sneakers / White; Sneakers / Khaki green; Sneakers / Mole; Sneakers / Unknown; Sneakers / Mole |
| b5 | v1 | 10 | None | None | None | ❌ max_results | Other accessories / Grey; Other accessories / Orange; Other accessories / Orange; Bag / Black; Bag / Lilac Purple |
| b5 | v2 | 10 | None | None | None | ❌ max_results | Other accessories / Grey; Other accessories / Orange; Other accessories / Orange; Bag / Black; Bag / Lilac Purple |

Zero-result in-catalogue queries in v2: r1 "best black jeans", r2 "recommend a summer dress", r3 "suggest white sneakers for men", r4 "popular hoodies", r5 "best winter jacket for women", r6 "recommend a black handbag"

Underfilled (1–9 results) in v2: none

Per-query NDCG@10: improved 77, unchanged 69, worse 4 (of 150)

OOC queries, results returned in v2: [(10, 23)]

## Why the 4 regressions happened

| Query | Cause |
|---|---|
| g146 pink bag, g86 green t-shirt, g88 blue t-shirt | The v1 rule that checks section text classified the children's section **"Kids Accessories, Swimwear & D"** as swimwear. That hid 16 children's T-shirts and 50 children's bags from tops and bags queries, which was an accidental audience filter. v2 classifies by product type, as S1 requires, so these items now compete. Children's items now rank highly in adult queries. **This is an audience problem, and S4 (downranking children's items) addresses it**; S1 and S2 don't. |
| p10 beige trench coat | The v2 vocabulary maps "trench" to the **Coat** type only, so coats rank above beige jackets. The catalogue types many trench coats as Jacket, and the label accepts both Coat and Jacket. A one-line vocabulary fix would map "trench" to Coat and Jacket. **I haven't made it, because it needs approval.** |

## Latency

- **End to end:** p95 112.0 ms (v1) vs 173.9 ms (v2). The v1 check, running **identical v1 code**, measured p95 250.0 ms with a maximum of 877 ms, so run-to-run machine noise is larger than this difference.
- **Reranking step on its own** (522 calls, real catalogue rows, 100 candidates each): v1 p50 1.00 ms, p95 3.58 ms; v2 p50 0.62 ms, p95 3.29 ms. **v2 adds no measurable reranking cost.**
- To judge the "+10% p95" criterion properly, both versions should be run back to back on an otherwise idle machine, ideally several times.

## Not changed by v2, as scoped

- The 6 recommendation queries still return 0 results (S10).
- All 23 out-of-catalogue queries return 10 results (S5).
- b2's floral and children's targets still fail (S3 and S4).
