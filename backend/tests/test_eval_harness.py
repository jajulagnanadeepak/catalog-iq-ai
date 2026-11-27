"""Tests for the WS-F search evaluation harness (stdlib only, no API/DB/index)."""

import csv
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from eval import compare as cmp
from eval import metrics
from eval.catalog import grade, load_catalog, normalise_id
from eval.run_eval import aggregate, load_queries, run, score_query

QUERIES = Path(__file__).resolve().parents[1] / "eval" / "queries.jsonl"
REAL_CSV = Path(__file__).resolve().parents[2] / "articles.csv"

FIELDS = ["article_id", "prod_name", "product_type_name", "product_group_name",
          "perceived_colour_master_name", "index_group_name", "section_name",
          "graphical_appearance_name", "detail_desc"]
ROWS = [
    ("0000000001", "Floral midi", "Dress", "Garment Full body", "Black", "Ladieswear", "Womens Casual", "All over pattern", "Floral print dress"),
    ("0000000002", "Solo dress", "Dress", "Garment Full body", "Black", "Ladieswear", "Womens Casual", "Solid", "Jersey dress"),
    ("0000000003", "Kids dress", "Dress", "Garment Full body", "Pink", "Baby/Children", "Kids Girl", "Solid", "Dress for girls"),
    ("0000000004", "Jump", "Jumpsuit/Playsuit", "Garment Full body", "Black", "Ladieswear", "Womens Casual", "Solid", "Jumpsuit"),
    ("0000000005", "Shirt", "Blouse", "Garment Upper body", "White", "Ladieswear", "Womens Casual", "Solid", "Blouse"),
    ("0000000006", "Laptop bag", "Bag", "Accessories", "Black", "Ladieswear", "Accessories", "Solid", "Bag for laptop"),
]


@pytest.fixture
def tiny_csv(tmp_path):
    path = tmp_path / "articles.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        w.writerows(ROWS)
    return path


@pytest.fixture
def catalog(tiny_csv):
    return load_catalog(tiny_csv)


DRESS = {"product_types": ["Dress"], "related_groups": ["Garment Full body"],
         "colours": ["Black"], "audience": "women"}


# ---------------- metrics ----------------

def test_ndcg_perfect_and_empty():
    hist = {"3": 5}
    assert metrics.ndcg_at_k([3, 3, 3, 3, 3], hist, 10) == pytest.approx(1.0)
    assert metrics.ndcg_at_k([], hist, 10) == 0.0


def test_ndcg_penalises_wrong_order_and_short_lists():
    hist = {"3": 2, "1": 10}
    best = metrics.ndcg_at_k([3, 3, 1], hist, 3)
    worse = metrics.ndcg_at_k([1, 3, 3], hist, 3)
    short = metrics.ndcg_at_k([3], hist, 3)
    assert best == pytest.approx(1.0) and worse < best and short < best


def test_ideal_uses_catalog_availability():
    # only 1 perfect item exists, so a list with 1 perfect + lower items is ideal
    assert metrics.ideal_gains({"3": 1, "2": 5}, 3) == [3.0, 2.0, 2.0]


def test_precision_counts_missing_as_irrelevant():
    assert metrics.precision_at_k([True, True], 5) == pytest.approx(0.4)


def test_mrr_and_percentile():
    assert metrics.mrr([False, False, True]) == pytest.approx(1 / 3)
    assert metrics.mrr([]) == 0.0
    assert metrics.percentile([1, 2, 3, 4], 50) == pytest.approx(2.5)


# ---------------- grading ----------------

def test_grade_full_match(catalog):
    g = grade(DRESS, catalog["0000000002"])
    assert (g.gain, g.max_gain, g.fully_relevant) == (3.0, 3.0, True)


def test_grade_wrong_audience_is_not_fully_relevant(catalog):
    g = grade(DRESS, catalog["0000000003"])  # kids pink dress
    assert g.type_ok and not g.fully_relevant and g.gain == 1.0


def test_grade_related_group_partial_credit(catalog):
    g = grade(DRESS, catalog["0000000004"])  # jumpsuit
    assert (g.type_ok, g.related, g.gain, g.fully_relevant) == (False, True, 0.5, False)


def test_grade_wrong_type_zero(catalog):
    assert grade(DRESS, catalog["0000000005"]).gain == 0.0


def test_attribute_terms_are_soft(catalog):
    spec = {**DRESS, "attribute_terms": ["floral"]}
    floral, plain = grade(spec, catalog["0000000001"]), grade(spec, catalog["0000000002"])
    assert floral.gain == 4.0 and plain.gain == 3.0
    assert floral.fully_relevant and plain.fully_relevant  # soft: not required


def test_unknown_item_scores_zero():
    assert grade(DRESS, None).gain == 0.0


def test_normalise_id_restores_leading_zeros():
    assert normalise_id(108775015) == "0108775015"
    assert normalise_id("p-001") == "p-001"


# ---------------- per-query scoring & targets ----------------

def _payload(*ids):
    return {"intent": {"intent": "occasion_search"},
            "products": [{"article_id": i, "product": {"_id": i}} for i in ids]}


def test_score_query_and_targets(catalog):
    spec = {"id": "b1", "group": "baseline", "query": "black dress for women", "top_k": 10,
            "expect": DRESS, "gain_hist": {"3": 1, "1": 1, "0.5": 1},
            "targets": {"min_results": 5, "type_at5_min": 2, "kids_at5_max": 0}}
    row = score_query(spec, 200, _payload("0000000002", "0000000003", "0000000005"), 12.0, catalog)
    assert row["n_results"] == 3 and row["type_at5"] == 2 and row["kids_at5"] == 1
    assert row["p@5"] == pytest.approx(0.2)
    assert row["targets"]["checks"] == {"min_results": False, "type_at5_min": True, "kids_at5_max": False}
    assert row["targets"]["passed"] is False


def test_out_of_catalog_scoring(catalog):
    spec = {"id": "x1", "group": "out_of_catalog", "query": "gaming laptop", "top_k": 10,
            "expect": {"out_of_catalog": True}, "targets": {"max_results": 0}}
    returned = score_query(spec, 200, _payload("0000000006"), 5.0, catalog)
    empty = score_query(spec, 200, {"products": []}, 5.0, catalog)
    flagged = score_query(spec, 200, {"products": [], "out_of_catalog": True}, 5.0, catalog)
    assert returned["ooc_correct"] is False and returned["targets"]["passed"] is False
    assert empty["ooc_correct"] is True and flagged["ooc_correct"] is True


def test_http_error_counts_as_zero_results(catalog):
    spec = {"id": "q", "group": "generated", "query": "x", "top_k": 10, "expect": DRESS,
            "gain_hist": {"3": 1}, "targets": {}}
    row = score_query(spec, 503, {"detail": "unavailable"}, 3.0, catalog)
    assert row["n_results"] == 0 and row["ndcg@10"] == 0.0


# ---------------- end-to-end against a fake API ----------------

class _FakeAPI(BaseHTTPRequestHandler):
    responses = {}
    requests = []

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).requests.append((self.path, body))
        payload = type(self).responses.get(body["query"], {"products": []})
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def fake_api():
    _FakeAPI.requests = []
    server = HTTPServer(("127.0.0.1", 0), _FakeAPI)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield _FakeAPI, f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_run_end_to_end_writes_reports(tmp_path, tiny_csv, catalog, fake_api):
    from eval.catalog import gain_histogram

    api, url = fake_api
    queries = tmp_path / "q.jsonl"
    specs = [
        {"id": "b1", "group": "baseline", "query": "black dress", "top_k": 10, "expect": DRESS,
         "gain_hist": gain_histogram(DRESS, catalog), "targets": {"min_results": 1}},
        {"id": "x1", "group": "out_of_catalog", "query": "gaming laptop", "top_k": 10,
         "expect": {"out_of_catalog": True}, "targets": {"max_results": 0}},
    ]
    queries.write_text("".join(json.dumps(s) + "\n" for s in specs), encoding="utf-8")
    # the ideal ranking: two black women's dresses, kids dress, jumpsuit
    api.responses = {"black dress": _payload("0000000002", "0000000001", "0000000003", "0000000004"),
                     "gaming laptop": _payload("0000000006")}

    report = run(url, "t", queries, tiny_csv, tmp_path / "reports")

    # read-only contract: only semantic-search POSTs, never a session_id
    assert {p for p, _ in api.requests} == {"/api/semantic-search"}
    assert all("session_id" not in b for _, b in api.requests)
    s = report["summary"]
    assert s["queries"] == 2 and s["out_of_catalog_correct_rate"] == 0.0
    assert s["in_catalog"]["ndcg@10"] == pytest.approx(1.0)
    assert s["ideal_inconsistent"] == 0
    assert (tmp_path / "reports" / "t.json").exists()
    md = (tmp_path / "reports" / "t.md").read_text(encoding="utf-8")
    assert "Owner baseline queries" in md and "gaming laptop" in md


def test_compare_detects_regression_and_mismatched_sets(tmp_path, tiny_csv, fake_api):
    api, url = fake_api
    queries = tmp_path / "q.jsonl"
    queries.write_text(json.dumps({"id": "b1", "group": "baseline", "query": "black dress", "top_k": 10,
                                   "expect": DRESS, "gain_hist": {"3": 2}, "targets": {}}) + "\n")
    api.responses = {"black dress": _payload("0000000002", "0000000001")}
    good = run(url, "good", queries, tiny_csv, tmp_path)
    api.responses = {"black dress": _payload("0000000005")}
    bad = run(url, "bad", queries, tiny_csv, tmp_path)

    text, code = cmp.compare(good, bad)
    assert code == 1 and "Per-query regressions (1)" in text
    _, same = cmp.compare(good, good)
    assert same == 0
    other = json.loads(json.dumps(bad))
    other["meta"]["queries_sha256"] = "different"
    assert cmp.compare(good, other)[1] == 1


# ---------------- the committed query set ----------------

def test_committed_query_set_is_well_formed():
    specs = load_queries(QUERIES)
    ids = [s["id"] for s in specs]
    assert len(ids) == len(set(ids)) and 150 <= len(specs) <= 300
    groups = {s["group"] for s in specs}
    assert {"baseline", "out_of_catalog", "generated", "kids", "recommendation"} <= groups
    assert sum(1 for s in specs if s["group"] == "out_of_catalog") >= 20
    for s in specs:
        if s["expect"].get("out_of_catalog"):
            assert s["targets"] == {"max_results": 0}
        else:
            assert s["expect"]["product_types"] and s["gain_hist"], s["id"]


def test_owner_baseline_queries_present_with_targets():
    by_id = {s["id"]: s for s in load_queries(QUERIES)}
    expected = {
        "b1": "black casual dress for women",
        "b2": "summer floral dress",
        "b3": "formal trousers for office wear",
        "b4": "comfortable running shoes",
        "b5": "gaming laptop with RTX graphics",
    }
    for qid, query in expected.items():
        assert by_id[qid]["query"] == query and by_id[qid]["targets"], qid
    assert by_id["b5"]["expect"] == {"out_of_catalog": True}
    assert by_id["b2"]["targets"]["min_results"] == 5


@pytest.mark.skipif(not REAL_CSV.exists(), reason="articles.csv not present")
def test_committed_query_set_is_reproducible():
    from eval.build_queries import main

    assert main(["--check", "--out", str(QUERIES)]) == 0


def test_stale_ideal_is_clamped_and_reported(catalog):
    spec = {"id": "q", "group": "generated", "query": "x", "top_k": 10, "expect": DRESS,
            "gain_hist": {"3": 1}, "targets": {}}  # claims 1 perfect item; 2 are returned
    row = score_query(spec, 200, _payload("0000000002", "0000000001"), 1.0, catalog)
    assert row["ndcg@10"] == 1.0 and row["ideal_inconsistent"] is True
