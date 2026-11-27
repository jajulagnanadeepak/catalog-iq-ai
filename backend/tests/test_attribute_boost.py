"""S3-lite: explicit pattern boost and navy synonym (v2 only, flag-gated)."""

import pytest

import routes.semantic_search as route
from config import Settings
from services.catalog_vocabulary import PATTERN_BOOST, PATTERN_SYNONYMS
from services.query_parser_v2 import extract_patterns
from services.semantic_reranker import SemanticReranker
from services.semantic_reranker_v2 import KIDS_PENALTY, SemanticRerankerV2

ADULT = "Womens Everyday Collection"
KIDS = "Kids Girl"


def item(aid, ptype, group, distance, description="", name=None, colour="Black", section=ADULT):
    return {
        "rank": 0, "article_id": aid, "distance": distance,
        "product": {
            "_id": aid, "article_id": aid, "name": name or f"Item {aid}",
            "product_type": ptype, "category": group, "department": "Dress",
            "section": section, "garment_group": "Dresses Ladies", "colour": colour,
            "description": description,
        },
    }


def pool(*items):
    for rank, it in enumerate(items, start=1):
        it["rank"] = rank
    return list(items)


def ids(results):
    return [r["article_id"] for r in results]


def keys(query):
    return [sorted(k) for k in extract_patterns(query)]


@pytest.fixture
def v2():
    return SemanticRerankerV2()


@pytest.fixture
def s3():
    return SemanticRerankerV2(attribute_boost=True)


# ------------------------------------------------------------ pattern extraction

@pytest.mark.parametrize(
    "pattern, synonym",
    [(p, s) for p, synonyms in PATTERN_SYNONYMS.items() for s in synonyms],
)
def test_every_approved_synonym_is_detected(pattern, synonym):
    requested = extract_patterns(f"{synonym} dress")
    assert len(requested) == 1 and pattern in requested[0]


@pytest.mark.parametrize(
    "query, expected",
    [
        ("floral dress", [["floral"]]),
        ("dress with flowers", [["floral"]]),
        ("striped t-shirt", [["stripe"]]),
        ("Stripes T-Shirt", [["stripe"]]),            # case-insensitive, plural
        ("checked shirt", [["check"]]),
        ("plaid shirt", [["check"]]),
        ("gingham dress", [["check"]]),
        ("lace dress", [["lace"]]),
        ("leopard dress", [["leopard"]]),
        ("animal print dress", [["leopard", "zebra"]]),  # one requirement, either pattern
        ("snake print boots", [["snake"]]),              # "snake print" consumes "print"
        ("polka dot dress", [["polka dot"]]),            # polka + dot = one requirement
        ("spotted blouse", []),                          # "spotted" is not an approved synonym
        ("printed t-shirt", [["print"]]),
        ("hoodie with a graphic print", [["graphic"], ["print"]]),
        ("striped floral dress", [["stripe"], ["floral"]]),
    ],
)
def test_pattern_extraction(query, expected):
    assert keys(query) == expected


@pytest.mark.parametrize(
    "query",
    [
        "lace-up boots",               # hyphenated: not lace
        "black lace-up sneakers",
        "check out this dress",        # verb
        "check the price of this dress",
        "check if this jacket is warm",
        "check-out dress",
        "blueprint dress",             # substrings inside other words
        "dotted",                      # not an approved synonym
        "spotlight jacket",
        "fingerprint scanner",
        "snakeskin boots",             # not an approved synonym
        "black dress for women",       # no pattern
        "",
    ],
)
def test_no_pattern_false_positives(query):
    assert extract_patterns(query) == []


def test_extraction_is_deterministic():
    q = "graphic print hoodie with stripes and checks"
    assert all(extract_patterns(q) == extract_patterns(q) for _ in range(5))


# ------------------------------------------------------------ ranking

def test_matching_product_gets_exact_boost_and_nonmatching_none(v2, s3):
    candidates = pool(
        item("plain", "Dress", "Garment Full body", 0.30, "Short dress in jersey."),
        item("floral", "Dress", "Garment Full body", 0.40, "Dress with a floral print."),
    )
    before = {r["article_id"]: r["score"] for r in v2.rerank("floral dress", candidates)}
    after = {r["article_id"]: r["score"] for r in s3.rerank("floral dress", candidates)}
    assert after["plain"] == before["plain"]                      # no penalty
    assert after["floral"] == pytest.approx(before["floral"] + PATTERN_BOOST, abs=1e-4)
    assert ids(s3.rerank("floral dress", candidates)) == ["floral", "plain"]


def test_missing_description_is_safe(s3):
    candidates = pool(
        item("none", "Dress", "Garment Full body", 0.30, description=None),
        item("floral", "Dress", "Garment Full body", 0.40, "Floral dress."),
    )
    candidates[0]["product"].pop("description")
    out = s3.rerank("floral dress", candidates)
    assert ids(out) == ["floral", "none"]


def test_pattern_in_name_counts(s3):
    candidates = pool(
        item("a", "T-shirt", "Garment Upper body", 0.30),
        item("b", "T-shirt", "Garment Upper body", 0.40, name="Striped tee"),
    )
    assert ids(s3.rerank("striped t-shirt", candidates))[0] == "b"


def test_lace_up_product_is_not_a_lace_match(s3):
    candidates = pool(
        item("laceup", "Boots", "Shoes", 0.30, "Lace-up boots in leather."),
        item("lace", "Boots", "Shoes", 0.40, "Boots with lace trim."),
    )
    out = {r["article_id"]: r["score"] for r in s3.rerank("lace boots", candidates)}
    plain = {r["article_id"]: r["score"] for r in SemanticRerankerV2().rerank("lace boots", candidates)}
    assert out["laceup"] == plain["laceup"]
    assert out["lace"] == pytest.approx(plain["lace"] + PATTERN_BOOST, abs=1e-4)


def test_type_hierarchy_preserved(s3):
    """A floral Top (tops backfill) never outranks a plain Blouse (the named type)."""
    candidates = pool(
        item("floral-top", "Top", "Garment Upper body", 0.10, "Top with a floral print."),
        item("plain-blouse", "Blouse", "Garment Upper body", 0.90, "Blouse in woven fabric."),
    )
    assert ids(s3.rerank("floral blouse", candidates)) == ["plain-blouse", "floral-top"]


def test_unrelated_category_never_enters(s3):
    candidates = pool(
        item("floral-dress", "Dress", "Garment Full body", 0.05, "Floral dress."),
        item("plain-blouse", "Blouse", "Garment Upper body", 0.90, "Blouse."),
    )
    assert ids(s3.rerank("floral blouse", candidates)) == ["plain-blouse"]


def test_no_boost_without_category(v2, s3):
    candidates = pool(
        item("a", "Dress", "Garment Full body", 0.30, "Dress."),
        item("b", "Top", "Garment Upper body", 0.40, "Floral top."),
    )
    assert s3.rerank("floral clothes", candidates) == v2.rerank("floral clothes", candidates)


def test_multiple_patterns_use_fraction(v2, s3):
    candidates = pool(
        item("both", "Dress", "Garment Full body", 0.50, "Striped dress with floral details."),
        item("one", "Dress", "Garment Full body", 0.50, "Striped dress."),
        item("none", "Dress", "Garment Full body", 0.50, "Dress."),
    )
    before = {r["article_id"]: r["score"] for r in v2.rerank("striped floral dress", candidates)}
    after = {r["article_id"]: r["score"] for r in s3.rerank("striped floral dress", candidates)}
    assert after["both"] == pytest.approx(before["both"] + PATTERN_BOOST, abs=1e-4)
    assert after["one"] == pytest.approx(before["one"] + PATTERN_BOOST / 2, abs=1e-4)
    assert after["none"] == before["none"]


def test_no_pattern_query_is_identical_to_v2(v2, s3):
    candidates = pool(
        item("a", "Dress", "Garment Full body", 0.30, "Floral dress."),
        item("b", "Dress", "Garment Full body", 0.40, "Striped dress."),
    )
    assert s3.rerank("black dress", candidates) == v2.rerank("black dress", candidates)


# ------------------------------------------------------------ colour

def _colour_pool():
    return pool(
        item("blue", "Sweater", "Garment Upper body", 0.40, colour="Dark Blue"),
        item("black", "Sweater", "Garment Upper body", 0.30, colour="Black"),
    )


def test_navy_maps_to_dark_blue_when_enabled(v2, s3):
    assert ids(s3.rerank("navy sweater", _colour_pool()))[0] == "blue"
    # flag off: navy matches nothing, ranking unchanged from v2
    assert ids(v2.rerank("navy sweater", _colour_pool()))[0] == "black"


@pytest.mark.parametrize("query", ["black sweater", "blue sweater", "red sweater", "grey sweater"])
def test_other_colours_unaffected(v2, s3, query):
    assert s3.rerank(query, _colour_pool()) == v2.rerank(query, _colour_pool())


# ------------------------------------------------------------ S4 / S2 interaction

def test_kids_penalty_still_applies_with_boost():
    both = SemanticRerankerV2(kids_penalty=KIDS_PENALTY, attribute_boost=True)
    s3_only = SemanticRerankerV2(attribute_boost=True)
    candidates = pool(
        item("kid", "Dress", "Garment Full body", 0.30, "Floral dress.", section=KIDS),
        item("adult", "Dress", "Garment Full body", 0.30, "Floral dress."),
    )
    a = {r["article_id"]: r["score"] for r in s3_only.rerank("floral dress", candidates)}
    b = {r["article_id"]: r["score"] for r in both.rerank("floral dress", candidates)}
    assert b["kid"] == pytest.approx(a["kid"] - KIDS_PENALTY, abs=1e-4)
    assert b["adult"] == a["adult"]
    assert ids(both.rerank("floral dress", candidates)) == ["adult", "kid"]


@pytest.mark.parametrize("query", ["girls party dress", "kids raincoat", "children's pyjamas"])
def test_kids_queries_without_pattern_unchanged(query):
    candidates = pool(
        item("k", "Dress", "Garment Full body", 0.30, "Floral dress.", section=KIDS),
        item("a", "Dress", "Garment Full body", 0.35, "Dress."),
    )
    s4 = SemanticRerankerV2(kids_penalty=KIDS_PENALTY)
    both = SemanticRerankerV2(kids_penalty=KIDS_PENALTY, attribute_boost=True)
    assert both.rerank(query, candidates) == s4.rerank(query, candidates)


def test_s2_backfill_and_fill_unchanged(v2, s3):
    candidates = pool(*[item(f"d{i}", "Dress", "Garment Full body", 0.1 + i / 100, "Floral dress.")
                        for i in range(8)] + [item("t", "Top", "Garment Upper body", 0.6, "Top.")])
    for limit in (5, 10, 50):
        assert len(s3.rerank("floral party clothes", candidates, limit=limit)) == \
            len(v2.rerank("floral party clothes", candidates, limit=limit))
        assert len(s3.rerank("floral dress", candidates, limit=limit)) == \
            len(v2.rerank("floral dress", candidates, limit=limit))


def test_deterministic(s3):
    candidates = pool(*[item(str(i), "Dress", "Garment Full body", 0.5,
                             "Floral dress." if i % 2 else "Dress.") for i in range(8)])
    first = ids(s3.rerank("floral dress", candidates))
    assert all(ids(s3.rerank("floral dress", candidates)) == first for _ in range(5))
    assert first == ["1", "3", "5", "7", "0", "2", "4", "6"]


def test_flag_off_instance_is_plain_v2_plus_s4():
    candidates = pool(
        item("a", "Dress", "Garment Full body", 0.30, "Floral dress."),
        item("b", "Sweater", "Garment Upper body", 0.40, colour="Dark Blue"),
    )
    off = SemanticRerankerV2(kids_penalty=KIDS_PENALTY, attribute_boost=False)
    s4 = SemanticRerankerV2(kids_penalty=KIDS_PENALTY)
    for q in ("floral dress", "navy sweater", "black dress"):
        assert off.rerank(q, candidates) == s4.rerank(q, candidates)


# ------------------------------------------------------------ feature flag

@pytest.fixture
def no_env(monkeypatch):
    for key in ("SEARCH_RERANK_VERSION", "SEARCH_V2_KIDS_DOWNRANK", "SEARCH_V2_ATTRIBUTE_BOOST"):
        monkeypatch.delenv(key, raising=False)


def test_flag_default_false(no_env):
    s = Settings(_env_file=None)
    assert s.search_v2_attribute_boost is False
    assert s.search_rerank_version == "v1"


def test_flag_from_environment(no_env, monkeypatch):
    monkeypatch.setenv("SEARCH_V2_ATTRIBUTE_BOOST", "true")
    assert Settings(_env_file=None).search_v2_attribute_boost is True


@pytest.mark.parametrize(
    "version, kids, attr, expected",
    [
        ("v1", False, False, "reranker"),
        ("v1", True, True, "reranker"),               # flags never affect v1
        ("v2", False, False, "reranker_v2"),
        ("v2", True, False, "reranker_v2_kids"),
        ("v2", False, True, "reranker_v2_attr"),
        ("v2", True, True, "reranker_v2_kids_attr"),
    ],
)
def test_route_selection(monkeypatch, version, kids, attr, expected):
    monkeypatch.setattr(route.settings, "search_rerank_version", version)
    monkeypatch.setattr(route.settings, "search_v2_kids_downrank", kids)
    monkeypatch.setattr(route.settings, "search_v2_attribute_boost", attr)
    assert route.active_reranker() is getattr(route, expected)


def test_route_instance_configuration():
    assert (route.reranker_v2.kids_penalty, route.reranker_v2.attribute_boost) == (0.0, False)
    assert (route.reranker_v2_kids.kids_penalty, route.reranker_v2_kids.attribute_boost) == (KIDS_PENALTY, False)
    assert (route.reranker_v2_attr.kids_penalty, route.reranker_v2_attr.attribute_boost) == (0.0, True)
    assert (route.reranker_v2_kids_attr.kids_penalty, route.reranker_v2_kids_attr.attribute_boost) == (KIDS_PENALTY, True)


@pytest.mark.parametrize("query", ["floral dress", "navy sweater", "striped t-shirt"])
async def test_v1_route_output_identical_with_all_v2_flags_on(monkeypatch, query):
    assert not hasattr(SemanticReranker(), "attribute_boost")
    candidates = pool(
        item("a", "Dress", "Garment Full body", 0.30, "Dress."),
        item("b", "Dress", "Garment Full body", 0.40, "Floral dress."),
        item("c", "Sweater", "Garment Upper body", 0.35, colour="Dark Blue"),
        item("d", "T-shirt", "Garment Upper body", 0.45, "Striped tee."),
    )

    async def fake_search(q, top_k=20):
        return [dict(c, product=dict(c["product"])) for c in candidates]

    monkeypatch.setattr(route, "semantic_search", fake_search)
    monkeypatch.setattr(route.intent_detector, "detect_intent",
                        lambda q: {"intent": "semantic_search", "confidence": 0.5})
    monkeypatch.setattr(route.settings, "search_rerank_version", "v1")

    responses = []
    for kids, attr in ((False, False), (True, True)):
        monkeypatch.setattr(route.settings, "search_v2_kids_downrank", kids)
        monkeypatch.setattr(route.settings, "search_v2_attribute_boost", attr)
        responses.append(await route.search_products(route.SearchRequest(query=query, top_k=10)))
    assert responses[0] == responses[1]
    assert "rerank_version" not in responses[0]
    assert responses[0]["products"] == SemanticReranker().rerank(query, candidates, limit=10)
