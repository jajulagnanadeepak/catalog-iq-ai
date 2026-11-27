"""S4: soft downranking of children's products for non-kids queries (v2 only)."""

import csv
from pathlib import Path

import pytest

import routes.semantic_search as route
from config import Settings
from services.catalog_vocabulary import KIDS_SECTIONS
from services.query_parser_v2 import allows_kids
from services.semantic_reranker import SemanticReranker
from services.semantic_reranker_v2 import KIDS_PENALTY, SemanticRerankerV2

ARTICLES_CSV = Path(__file__).resolve().parents[2] / "articles.csv"

ADULT = "Womens Everyday Collection"
KIDS = "Kids Accessories, Swimwear & D"


def item(aid, ptype, group, section, distance, colour="Green", name=None):
    return {
        "rank": 0, "article_id": aid, "distance": distance,
        "product": {
            "_id": aid, "article_id": aid, "name": name or f"Item {aid}",
            "product_type": ptype, "category": group, "department": "Jersey",
            "section": section, "garment_group": "Jersey Basic", "colour": colour,
            "description": "",
        },
    }


def pool(*items):
    for rank, it in enumerate(items, start=1):
        it["rank"] = rank
    return list(items)


def ids(results):
    return [r["article_id"] for r in results]


@pytest.fixture
def v2():
    return SemanticRerankerV2()


@pytest.fixture
def s4():
    return SemanticRerankerV2(kids_penalty=KIDS_PENALTY)


# ------------------------------------------------------------------ catalogue

@pytest.mark.skipif(not ARTICLES_CSV.exists(), reason="articles.csv not present")
def test_kids_sections_match_catalogue_ground_truth_exactly():
    kids, adult = set(), set()
    with open(ARTICLES_CSV, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            section = " ".join(row["section_name"].lower().split())
            (kids if row["index_group_name"] == "Baby/Children" else adult).add(section)
    assert kids == set(KIDS_SECTIONS)
    assert not (kids & adult)  # no section mixes children's and adult products


@pytest.mark.parametrize(
    "section, expected",
    [
        ("Kids Boy", True), ("Baby Girl", True), ("Young Girl", True),
        ("Kids & Baby Shoes", True), ("Kids Accessories, Swimwear & D", True),
        ("Divided Basics", False), ("Womens Everyday Collection", False),
        ("Menswear", False), ("Ladies H&M Sport", False), ("", False), (None, False),
    ],
)
def test_kids_product_detection(section, expected):
    assert SemanticRerankerV2._is_kids_product({"section": section}) is expected


def test_product_without_section_is_not_kids():
    assert SemanticRerankerV2._is_kids_product({}) is False


# ------------------------------------------------------------------ query side

@pytest.mark.parametrize(
    "query",
    [
        # eval kids queries k1-k6
        "girls party dress", "baby bodysuit", "sneakers for boys", "kids raincoat",
        "children's pyjamas", "winter hat for kids",
        # other kids words
        "childrens shoes", "kids' shoes", "toddler jacket", "infant socks",
        "newborn gift set", "junior football shirt", "boy's jacket", "babies hat",
        # ambiguous audience -> no penalty either
        "teen hoodie", "school uniform", "dress for my daughter", "clothes for my son",
        "family pyjamas", "mother and daughter matching dresses",
    ],
)
def test_queries_that_allow_kids(query):
    assert allows_kids(query) is True


@pytest.mark.parametrize(
    "query",
    [
        "green t-shirt", "blue t-shirt", "pink bag", "black casual dress for women",
        # adult phrases containing a kids word
        "baby pink dress", "baby blue shirt for men", "girls' night dress",
        "girls night out dress", "babydoll dress", "baby-doll top",
        # word boundaries / false positives
        "boyfriend jeans", "seasonal coat", "kidskin gloves", "babylon print scarf",
        "schooled", "parson shirt",
    ],
)
def test_queries_that_do_not_allow_kids(query):
    assert allows_kids(query) is False


def test_adult_phrase_does_not_hide_a_real_kids_word():
    assert allows_kids("baby pink dress for girls") is True


# ------------------------------------------------------------------ ranking

def _regression_pool(ptype, group):
    # The kids item is marginally closer, as in the eval regressions.
    return pool(
        item("kid", ptype, group, KIDS, 0.30),
        item("adult", ptype, group, ADULT, 0.35),
    )


@pytest.mark.parametrize(
    "query, ptype, group",
    [
        ("green t-shirt", "T-shirt", "Garment Upper body"),
        ("blue t-shirt", "T-shirt", "Garment Upper body"),
        ("pink bag", "Bag", "Accessories"),
    ],
)
def test_known_regressions_adult_item_ranks_first(v2, s4, query, ptype, group):
    candidates = _regression_pool(ptype, group)
    assert ids(v2.rerank(query, candidates)) == ["kid", "adult"]   # current v2
    assert ids(s4.rerank(query, candidates)) == ["adult", "kid"]   # S4


def test_penalty_is_soft_much_stronger_kids_item_still_wins(s4):
    candidates = pool(
        item("kid", "T-shirt", "Garment Upper body", KIDS, 0.05),
        item("adult", "T-shirt", "Garment Upper body", ADULT, 2.50),
    )
    assert ids(s4.rerank("green t-shirt", candidates)) == ["kid", "adult"]


def test_penalty_size_and_reported_score(v2, s4):
    candidates = _regression_pool("T-shirt", "Garment Upper body")
    before = {r["article_id"]: r["score"] for r in v2.rerank("green t-shirt", candidates)}
    after = {r["article_id"]: r["score"] for r in s4.rerank("green t-shirt", candidates)}
    assert after["adult"] == before["adult"]
    assert after["kid"] == pytest.approx(before["kid"] - KIDS_PENALTY, abs=1e-4)


def test_kids_products_never_removed_and_count_unchanged(v2, s4):
    candidates = pool(*[
        item(f"k{i}", "T-shirt", "Garment Upper body", KIDS, 0.1 + i / 100) for i in range(8)
    ] + [
        item(f"a{i}", "T-shirt", "Garment Upper body", ADULT, 0.5 + i / 100) for i in range(4)
    ])
    for limit in (5, 10, 50):
        out_v2, out_s4 = v2.rerank("green t-shirt", candidates, limit=limit), \
            s4.rerank("green t-shirt", candidates, limit=limit)
        assert len(out_s4) == len(out_v2)
        if limit >= 12:
            assert set(ids(out_s4)) == set(ids(out_v2))  # same products, reordered
    # with room for everything, all 8 kids products are still returned
    assert sum(i.startswith("k") for i in ids(s4.rerank("green t-shirt", candidates, limit=50))) == 8


@pytest.mark.parametrize(
    "query",
    ["girls party dress", "baby bodysuit", "sneakers for boys", "kids raincoat",
     "children's pyjamas", "winter hat for kids", "teen hoodie"],
)
def test_kids_and_ambiguous_queries_identical_to_v2(v2, s4, query):
    candidates = pool(
        item("k1", "Dress", "Garment Full body", KIDS, 0.20),
        item("a1", "Dress", "Garment Full body", ADULT, 0.25),
        item("k2", "Sneakers", "Shoes", "Kids & Baby Shoes", 0.30),
        item("a2", "Bodysuit", "Garment Upper body", ADULT, 0.35),
        item("k3", "Hat/beanie", "Accessories", KIDS, 0.40),
        item("k4", "Pyjama set", "Nightwear", "Kids Girl", 0.45),
        item("k5", "Hoodie", "Garment Upper body", "Young Boy", 0.50),
        item("k6", "Jacket", "Garment Upper body", "Kids Outerwear", 0.55),
    )
    assert v2.rerank(query, candidates) == s4.rerank(query, candidates)


def test_s1_type_first_ordering_preserved(s4):
    # A kids bikini top (the named type) still ranks above adult backfill.
    candidates = pool(
        item("adult-bottom", "Swimwear bottom", "Swimwear", ADULT, 0.10, "Pink"),
        item("kid-top", "Bikini top", "Swimwear", KIDS, 0.40, "Pink"),
        item("adult-top", "Bikini top", "Swimwear", ADULT, 0.45, "Pink"),
    )
    assert ids(s4.rerank("pink bikini top", candidates)) == ["adult-top", "kid-top", "adult-bottom"]


def test_s2_backfill_preserved(v2, s4):
    candidates = pool(*[
        item(f"k{i}", "Dress", "Garment Full body", KIDS, 0.1 + i / 100) for i in range(8)
    ] + [item("t0", "Top", "Garment Upper body", ADULT, 0.6)])
    out = s4.rerank("clothes for a party", candidates, limit=5)
    assert len(out) == 5 == len(v2.rerank("clothes for a party", candidates, limit=5))


def test_deterministic(s4):
    candidates = pool(*[
        item(str(i), "T-shirt", "Garment Upper body", KIDS if i % 2 else ADULT, 0.5) for i in range(8)
    ])
    first = ids(s4.rerank("green t-shirt", candidates))
    for _ in range(5):
        assert ids(s4.rerank("green t-shirt", candidates)) == first
    # adults first, each tier in FAISS order
    assert first == ["0", "2", "4", "6", "1", "3", "5", "7"]


def test_zero_penalty_is_plain_v2(v2):
    candidates = _regression_pool("T-shirt", "Garment Upper body")
    assert SemanticRerankerV2(kids_penalty=0.0).rerank("green t-shirt", candidates) == \
        v2.rerank("green t-shirt", candidates)


# ------------------------------------------------------------------ feature flag

@pytest.fixture
def no_env(monkeypatch):
    for key in ("SEARCH_RERANK_VERSION", "SEARCH_V2_KIDS_DOWNRANK"):
        monkeypatch.delenv(key, raising=False)


def test_flag_defaults(no_env):
    s = Settings(_env_file=None)
    assert s.search_rerank_version == "v1"
    assert s.search_v2_kids_downrank is False


def test_flag_from_environment(no_env, monkeypatch):
    monkeypatch.setenv("SEARCH_V2_KIDS_DOWNRANK", "true")
    assert Settings(_env_file=None).search_v2_kids_downrank is True


@pytest.mark.parametrize(
    "version, kids_flag, expected",
    [
        ("v1", False, "reranker"),
        ("v1", True, "reranker"),          # flag has no effect on v1
        ("v2", False, "reranker_v2"),      # S1 + S2 only, as before
        ("v2", True, "reranker_v2_kids"),  # S4 enabled
    ],
)
def test_route_selection(monkeypatch, version, kids_flag, expected):
    monkeypatch.setattr(route.settings, "search_rerank_version", version)
    monkeypatch.setattr(route.settings, "search_v2_kids_downrank", kids_flag)
    assert route.active_reranker() is getattr(route, expected)


def test_route_instances():
    assert type(route.reranker) is SemanticReranker
    assert route.reranker_v2.kids_penalty == 0.0
    assert route.reranker_v2_kids.kids_penalty == KIDS_PENALTY


def test_v1_ignores_kids_products(v2):
    # v1 has no audience logic; S4 code never runs for v1.
    v1 = SemanticReranker()
    assert not hasattr(v1, "kids_penalty")
    candidates = pool(
        item("kid", "T-shirt", "Garment Upper body", "Kids Boy", 0.30),
        item("adult", "T-shirt", "Garment Upper body", ADULT, 0.35),
    )
    assert ids(v1.rerank("green t-shirt", candidates)) == ["kid", "adult"]
    # Known v1 quirk (the S1 root cause): its section rule treats
    # "Kids Accessories, Swimwear & D" as swimwear and filters it out.
    assert ids(v1.rerank("green t-shirt", _regression_pool("T-shirt", "Garment Upper body"))) == ["adult"]
