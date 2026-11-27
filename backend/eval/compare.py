"""
Compare two evaluation reports produced from the same query set.

    python -m eval.compare eval/reports/v1.json eval/reports/v2.json

Prints metric deltas, per-group deltas, target changes and per-query
regressions (NDCG@10 drop >= 0.10, or fewer fully relevant items in the top 5).
Exits 1 if the query sets differ or any regression is found, 0 otherwise.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REGRESSION_NDCG_DROP = 0.10


def compare(a: dict, b: dict) -> tuple[str, int]:
    lines = []
    if a["meta"]["queries_sha256"] != b["meta"]["queries_sha256"]:
        return "Query sets differ - comparison is not valid.", 1

    sa, sb = a["summary"], b["summary"]
    la, lb = a["meta"]["label"], b["meta"]["label"]
    lines += [f"# {la} → {lb}", "", "| Metric | " + la + " | " + lb + " | Δ |", "|---|---|---|---|"]

    def row(name, x, y):
        lines.append(f"| {name} | {x} | {y} | {round(y - x, 4):+} |")

    for m in sa["in_catalog"]:
        row(m, sa["in_catalog"][m], sb["in_catalog"][m])
    row("zero_result_rate", sa["zero_result_rate"], sb["zero_result_rate"])
    row("kids_at5_rate_non_kids_queries", sa["kids_at5_rate_non_kids_queries"], sb["kids_at5_rate_non_kids_queries"])
    row("out_of_catalog_correct_rate", sa["out_of_catalog_correct_rate"], sb["out_of_catalog_correct_rate"])
    row("latency_p95_ms", sa["latency_ms"]["p95"], sb["latency_ms"]["p95"])
    row("targets_passed", sa["targets"]["passed"], sb["targets"]["passed"])

    lines += ["", "## By group (NDCG@10 or OOC correct rate)", "", f"| group | {la} | {lb} | Δ |", "|---|---|---|---|"]
    for g, va in sa["by_group"].items():
        vb = sb["by_group"].get(g, {})
        key = "ndcg@10" if "ndcg@10" in va else "ooc_correct_rate"
        lines.append(f"| {g} | {va[key]} | {vb.get(key, 0)} | {round(vb.get(key, 0) - va[key], 4):+} |")

    qa = {r["id"]: r for r in a["queries"]}
    regressions = []
    for r in b["queries"]:
        old = qa.get(r["id"])
        if old is None:
            continue
        if "ndcg@10" in r:
            if old["ndcg@10"] - r["ndcg@10"] >= REGRESSION_NDCG_DROP or r["p@5"] < old["p@5"]:
                regressions.append(f"| {r['id']} | {r['query']} | NDCG {old['ndcg@10']} → {r['ndcg@10']} · "
                                   f"P@5 {old['p@5']} → {r['p@5']} |")
        elif old.get("ooc_correct") and not r.get("ooc_correct"):
            regressions.append(f"| {r['id']} | {r['query']} | out-of-catalog no longer handled |")
        if old["targets"]["passed"] and r["targets"]["passed"] is False:
            regressions.append(f"| {r['id']} | {r['query']} | target now failing |")

    lines += ["", f"## Per-query regressions ({len(regressions)})", ""]
    lines += (["| id | query | change |", "|---|---|---|"] + regressions) if regressions else ["None."]
    return "\n".join(lines) + "\n", 1 if regressions else 0


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2:
        print(__doc__)
        return 2
    a, b = (json.loads(Path(p).read_text(encoding="utf-8")) for p in argv)
    text, code = compare(a, b)
    print(text)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
