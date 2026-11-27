# Search evaluation harness (Phase 1, WS-F)

Measures `POST /api/semantic-search` against a fixed, labelled query set. It is
read-only: it sends search requests without a `session_id` and grades the
returned `article_id`s against `articles.csv`. It never connects to MongoDB
and never touches the FAISS index. Standard library only.

| File | Purpose |
|---|---|
| `queries.jsonl` | 174 labelled queries (committed; rebuilt deterministically) |
| `build_queries.py` | Builds `queries.jsonl` from `articles.csv` (`--check` verifies it is current) |
| `catalog.py` | Attribute lookup and graded relevance |
| `metrics.py` | NDCG@10, P@k, MRR, percentiles |
| `run_eval.py` | Runs the set against a live API → `reports/<label>.json` and `.md` |
| `compare.py` | Diffs two reports (same query set) and lists per-query regressions |
| `BASELINE.md` | Owner's manual baseline (v0), root causes, proposed changes |

## Query set

| Group | n | What it tests |
|---|---|---|
| `baseline` | 5 | Owner's Q1–Q5, with explicit acceptance targets |
| `generated` | 100 | "<colour> <type> [for women/men]" combinations the catalog can satisfy (≥10 fully relevant items each) |
| `occasion` | 12 | Use cases (office, party, gym, beach, college student, …) |
| `attribute` | 14 | Patterns and materials (striped, denim, floral, leather, linen, …) |
| `kids` | 6 | Children's queries, where children's items **are** correct |
| `synonym` | 8 | pants/jumper/trainers/tee/jeans/swimming costume |
| `recommendation` | 6 | Queries containing best/recommend/suggest/popular (they take a separate code path) |
| `out_of_catalog` | 23 | Products this fashion catalog does not carry (laptops, TVs, …) |

## Relevance labels

Labels come from catalog attributes, not hand-picked products:

- **Type:** `product_type_name` must be one of the query's acceptable types. A product in the same product group (for example a jumpsuit for a dress query) earns partial credit (0.5).
- **Colour:** `perceived_colour_master_name`.
- **Audience:** `index_group_name`. *adult* means not Baby/Children; *women* means Ladieswear, Divided, or Sport-ladies; *men* means Menswear or Sport-men. Queries without a stated audience expect adult items, following the owner's Q2 finding.
- **Attribute terms** (floral, leather, …): matched in the name, description or `graphical_appearance_name`. These are **soft**: they add gain but are not required.

Gain = 1 + one point per satisfied constraint, for the right type only. **Fully relevant** means the right type, the right colour and the right audience. NDCG@10 uses a true ideal computed from how many catalog items exist at each gain level (`gain_hist`).

## Metrics

| Metric | Definition |
|---|---|
| NDCG@10 | Graded ranking quality against the catalog's ideal ranking (0–1) |
| P@5, P@10 | Share of positions holding a fully relevant item. Missing results count as misses. |
| MRR | 1 / rank of the first fully relevant item |
| fill rate | Results returned ÷ `top_k` |
| zero-result rate | In-catalog queries that return nothing |
| kids@5 rate | Children's items in the top 5 for non-kids queries |
| OOC correct | Out-of-catalog query answered with no products or `out_of_catalog: true` |
| latency | Client-side p50 / p95 / max |
| targets | Per-query acceptance checks (Q1–Q5 now; more can be added) |

## Running it

```bash
cd backend
# terminal 1: start the API as usual (uses your .env and the existing index)
uvicorn main:app --port 8000
# terminal 2:
python -m eval.run_eval --label v1          # writes eval/reports/v1.{json,md}
# later, after starting the API with SEARCH_RERANK_VERSION=v2:
python -m eval.run_eval --label v2
python -m eval.compare eval/reports/v1.json eval/reports/v2.json
```

A full run is 174 requests plus one warm-up. Rebuild the query set only if `articles.csv` changes: `python -m eval.build_queries` (about 30 s), then commit the new `queries.jsonl`. Reports from different query sets can't be compared, and `compare.py` refuses to do it.
