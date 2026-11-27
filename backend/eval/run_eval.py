"""
Run the search evaluation against a running CatalogIQ API.

    # from backend/, with the API running (uvicorn main:app --port 8000)
    python -m eval.run_eval --label v1
    python -m eval.run_eval --label v2 --assert-targets   # later, for v2

Read-only: sends `POST /api/semantic-search` requests without a session_id
(no personalisation, nothing is written) and grades the returned
article_ids against articles.csv. Writes reports/<label>.json and .md.
Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from eval.catalog import DEFAULT_CSV, grade, load_catalog, normalise_id
from eval.metrics import mean, mrr, ndcg_at_k, percentile, precision_at_k

HERE = Path(__file__).resolve().parent
QUERIES = HERE / "queries.jsonl"
REPORTS = HERE / "reports"


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def call_search(base_url: str, query: str, top_k: int, timeout: float) -> tuple[int, dict, float]:
    body = json.dumps({"query": query, "top_k": top_k}).encode()
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/semantic-search",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        return 0, {"error": f"{type(exc).__name__}: {exc}"}, (time.perf_counter() - start) * 1000
    latency = (time.perf_counter() - start) * 1000
    try:
        payload = json.loads(raw.decode() or "{}")
    except ValueError:
        payload = {"error": "non-JSON response"}
    return status, payload, latency


def result_ids(payload: dict) -> list[str]:
    ids = []
    for item in payload.get("products") or []:
        product = item.get("product") or {}
        aid = item.get("article_id") or product.get("article_id") or product.get("_id")
        if aid is not None:
            ids.append(normalise_id(aid))
    return ids


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------
def score_query(spec: dict, status: int, payload: dict, latency_ms: float, catalog) -> dict:
    expect = spec["expect"]
    k = spec.get("top_k", 10)
    ids = result_ids(payload) if status == 200 else []
    row = {
        "id": spec["id"], "group": spec["group"], "query": spec["query"],
        "status": status, "latency_ms": round(latency_ms, 1),
        "intent": (payload.get("intent") or {}).get("intent"),
        "n_results": len(ids),
        "out_of_catalog_flag": bool(payload.get("out_of_catalog")),
        "error": payload.get("error") if status != 200 else None,
        "top5": [],
    }

    if expect.get("out_of_catalog"):
        row["ooc_correct"] = row["out_of_catalog_flag"] or (status == 200 and not ids)
        row["top5"] = [_describe(catalog.get(i), i) for i in ids[:5]]
        row["targets"] = _check_targets(spec.get("targets", {}), row)
        return row

    grades = [grade(expect, catalog.get(i)) for i in ids]
    gains = [g.gain for g in grades]
    full = [g.fully_relevant for g in grades]
    top5 = grades[:5]
    items5 = [catalog.get(i) for i in ids[:5]]
    raw_ndcg = ndcg_at_k(gains, spec["gain_hist"], 10)

    row.update({
        "unknown_ids": sum(1 for i in ids if i not in catalog),
        "fill_rate": min(1.0, len(ids) / k),
        "ndcg@10": round(min(1.0, raw_ndcg), 4),
        # >1 means gain_hist is stale vs articles.csv: rebuild queries.jsonl
        "ideal_inconsistent": raw_ndcg > 1.0 + 1e-9,
        "p@5": precision_at_k(full, 5),
        "p@10": precision_at_k(full, 10),
        "mrr": round(mrr(full), 4),
        "type_at5": sum(1 for g in top5 if g.type_ok),
        "group_at5": sum(1 for g in top5 if g.type_ok or g.related),
        "kids_at5": sum(1 for it in items5 if it is not None and it.is_kids),
        "colour_at5": sum(1 for g in top5 if g.colour_ok) if expect.get("colours") else None,
        "attribute_at5": (sum(1 for g in top5 if g.attribute_ok)
                          if (expect.get("attribute_terms") or expect.get("attribute_appearances")) else None),
        "top5": [_describe(it, i) for it, i in zip(items5, ids[:5])],
    })
    row["targets"] = _check_targets(spec.get("targets", {}), row)
    return row


def _describe(item, aid) -> str:
    if item is None:
        return f"{aid} (not in articles.csv)"
    kid = " [kids]" if item.is_kids else ""
    return f"{item.product_type} / {item.colour}{kid}"


def _check_targets(targets: dict, row: dict) -> dict:
    checks = {}
    for name, bound in targets.items():
        if name == "min_results":
            checks[name] = row["n_results"] >= bound
        elif name == "max_results":
            checks[name] = row["n_results"] <= bound
        elif name.endswith("_min"):
            checks[name] = (row.get(name[:-4]) or 0) >= bound
        elif name.endswith("_max"):
            checks[name] = (row.get(name[:-4]) or 0) <= bound
        else:
            raise ValueError(f"unknown target {name}")
    return {"checks": checks, "passed": all(checks.values()) if checks else None}


# --------------------------------------------------------------------------
# Aggregation and reporting
# --------------------------------------------------------------------------
METRICS = ["ndcg@10", "p@5", "p@10", "mrr", "fill_rate"]


def aggregate(rows: list[dict]) -> dict:
    in_cat = [r for r in rows if "ooc_correct" not in r]
    ooc = [r for r in rows if "ooc_correct" in r]
    adult = [r for r in in_cat if r["group"] != "kids"]
    lat = [r["latency_ms"] for r in rows if r["status"] == 200]
    summary = {
        "queries": len(rows),
        "in_catalog": {m: round(mean([r[m] for r in in_cat]), 4) for m in METRICS},
        "zero_result_rate": round(mean([1.0 if r["n_results"] == 0 else 0.0 for r in in_cat]), 4),
        "kids_at5_rate_non_kids_queries": round(
            mean([r["kids_at5"] / 5 for r in adult if r["n_results"]]), 4),
        "out_of_catalog_correct_rate": round(mean([1.0 if r["ooc_correct"] else 0.0 for r in ooc]), 4),
        "errors": sum(1 for r in rows if r["status"] != 200),
        "unknown_ids": sum(r.get("unknown_ids", 0) for r in in_cat),
        "ideal_inconsistent": sum(1 for r in in_cat if r.get("ideal_inconsistent")),
        "latency_ms": {"p50": round(percentile(lat, 50), 1), "p95": round(percentile(lat, 95), 1),
                       "max": round(max(lat), 1) if lat else 0.0},
        "targets": {
            "evaluated": sum(1 for r in rows if r["targets"]["passed"] is not None),
            "passed": sum(1 for r in rows if r["targets"]["passed"]),
        },
        "by_group": {},
    }
    for group in sorted({r["group"] for r in rows}):
        g = [r for r in rows if r["group"] == group]
        if group == "out_of_catalog" or all("ooc_correct" in r for r in g):
            summary["by_group"][group] = {
                "n": len(g),
                "ooc_correct_rate": round(mean([1.0 if r.get("ooc_correct") else 0.0 for r in g]), 4),
            }
        else:
            gi = [r for r in g if "ooc_correct" not in r]
            summary["by_group"][group] = {"n": len(g), **{m: round(mean([r[m] for r in gi]), 4) for m in METRICS},
                                          "zero_result_rate": round(mean([1.0 if r["n_results"] == 0 else 0.0
                                                                           for r in gi]), 4)}
    return summary


def to_markdown(report: dict) -> str:
    m, s = report["meta"], report["summary"]
    out = [f"# Search evaluation: `{m['label']}`", "",
           f"- Run: {m['timestamp']} · API `{m['base_url']}` · git `{m['git_commit']}`",
           f"- Query set: {s['queries']} queries · sha256 `{m['queries_sha256'][:12]}`",
           "- Labels derived from articles.csv attributes; requests sent without session_id (no personalisation).",
           "", "## Summary", "",
           "| Metric | Value |", "|---|---|"]
    for k, v in s["in_catalog"].items():
        out.append(f"| {k} (in-catalog mean) | {v} |")
    out += [f"| zero-result rate (in-catalog) | {s['zero_result_rate']} |",
            f"| children's items in top 5 (non-kids queries) | {s['kids_at5_rate_non_kids_queries']} |",
            f"| out-of-catalog handled correctly | {s['out_of_catalog_correct_rate']} |",
            f"| latency p50 / p95 / max (ms) | {s['latency_ms']['p50']} / {s['latency_ms']['p95']} / {s['latency_ms']['max']} |",
            f"| HTTP errors | {s['errors']} |",
            f"| result ids not in articles.csv | {s['unknown_ids']} |",
            f"| queries with stale ideal (rebuild queries.jsonl if > 0) | {s['ideal_inconsistent']} |",
            f"| query targets passed | {s['targets']['passed']} / {s['targets']['evaluated']} |",
            "", "## By group", "", "| Group | n | NDCG@10 | P@5 | MRR | fill | zero-result | OOC correct |",
            "|---|---|---|---|---|---|---|---|"]
    for g, v in s["by_group"].items():
        out.append(f"| {g} | {v['n']} | {v.get('ndcg@10', '–')} | {v.get('p@5', '–')} | {v.get('mrr', '–')} | "
                   f"{v.get('fill_rate', '–')} | {v.get('zero_result_rate', '–')} | {v.get('ooc_correct_rate', '–')} |")

    rows = report["queries"]
    out += ["", "## Owner baseline queries (Q1–Q5) and targets", "",
            "| id | query | intent | n | type@5 | kids@5 | NDCG@10 | targets | top 5 |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["group"] == "baseline":
            t = r["targets"]
            tflag = "✅" if t["passed"] else "❌ " + ", ".join(k for k, ok in t["checks"].items() if not ok)
            out.append(f"| {r['id']} | {r['query']} | {r['intent']} | {r['n_results']} | {r.get('type_at5', '–')} | "
                       f"{r.get('kids_at5', '–')} | {r.get('ndcg@10', '–')} | {tflag} | {'; '.join(r['top5'])} |")

    worst = sorted((r for r in rows if "ndcg@10" in r), key=lambda r: r["ndcg@10"])[:15]
    out += ["", "## 15 weakest in-catalog queries", "", "| id | group | query | intent | n | NDCG@10 | P@5 | top 5 |",
            "|---|---|---|---|---|---|---|---|"]
    for r in worst:
        out.append(f"| {r['id']} | {r['group']} | {r['query']} | {r['intent']} | {r['n_results']} | "
                   f"{r['ndcg@10']} | {r['p@5']} | {'; '.join(r['top5'])} |")

    ooc = [r for r in rows if "ooc_correct" in r and r["group"] == "out_of_catalog"]
    out += ["", "## Out-of-catalog queries", "", "| id | query | n | correct | top 3 |", "|---|---|---|---|---|"]
    for r in ooc:
        out.append(f"| {r['id']} | {r['query']} | {r['n_results']} | {'✅' if r['ooc_correct'] else '❌'} | "
                   f"{'; '.join(r['top5'][:3])} |")
    errs = [r for r in rows if r["status"] != 200]
    if errs:
        out += ["", "## Errors", ""] + [f"- {r['id']} `{r['query']}`: HTTP {r['status']} {r['error']}" for r in errs]
    return "\n".join(out) + "\n"


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, cwd=HERE, timeout=5).stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


def load_queries(path: Path = QUERIES) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run(base_url: str, label: str, queries_path: Path, csv_path: Path, out_dir: Path,
        timeout: float = 60.0, only_group: str | None = None) -> dict:
    catalog = load_catalog(csv_path)
    specs = load_queries(queries_path)
    if only_group:
        specs = [s for s in specs if s["group"] == only_group]

    # Warm-up (first request may load lazily / fill caches); not scored.
    call_search(base_url, "warm up", 5, timeout)

    rows = []
    for n, spec in enumerate(specs, start=1):
        status, payload, latency = call_search(base_url, spec["query"], spec.get("top_k", 10), timeout)
        rows.append(score_query(spec, status, payload, latency, catalog))
        print(f"[{n:>3}/{len(specs)}] {spec['id']:<5} {status} {rows[-1]['n_results']:>2} results "
              f"{latency:7.1f} ms  {spec['query']}")

    report = {
        "meta": {
            "label": label, "base_url": base_url,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git_commit": _git_commit(), "python": platform.python_version(),
            "queries_sha256": hashlib.sha256(queries_path.read_bytes()).hexdigest(),
        },
        "summary": aggregate(rows),
        "queries": rows,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{label}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / f"{label}.md").write_text(to_markdown(report), encoding="utf-8")
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="CatalogIQ search evaluation")
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--label", required=True, help="report name, e.g. v1 or v2")
    p.add_argument("--queries", default=str(QUERIES))
    p.add_argument("--csv", default=str(DEFAULT_CSV))
    p.add_argument("--out-dir", default=str(REPORTS))
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--group", help="only run one query group")
    p.add_argument("--assert-targets", action="store_true",
                   help="exit 1 if any per-query target fails (use for v2)")
    args = p.parse_args(argv)

    report = run(args.base_url, args.label, Path(args.queries), Path(args.csv), Path(args.out_dir),
                 args.timeout, args.group)
    s = report["summary"]
    print(f"\nNDCG@10 {s['in_catalog']['ndcg@10']}  P@5 {s['in_catalog']['p@5']}  "
          f"zero-result {s['zero_result_rate']}  OOC-correct {s['out_of_catalog_correct_rate']}  "
          f"p95 {s['latency_ms']['p95']} ms  targets {s['targets']['passed']}/{s['targets']['evaluated']}")
    print(f"Report: {Path(args.out_dir) / (args.label + '.md')}")
    if s["errors"]:
        print(f"WARNING: {s['errors']} requests failed - see the Errors section")
    if args.assert_targets and s["targets"]["passed"] < s["targets"]["evaluated"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
