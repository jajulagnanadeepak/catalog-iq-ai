"""S5 hard tier: out-of-catalogue detection (v2 only, flag-gated)."""

import json
from pathlib import Path

import pytest

import routes.semantic_search as route
from config import Settings
from services.catalog_scope import REASON_PREFIX, classify
from services.catalog_vocabulary import UNSUPPORTED_DOMAINS
from services.semantic_reranker import SemanticReranker

QUERIES = Path(__file__).resolve().parents[1] / "eval" / "queries.jsonl"

# Held-out sets from the S5 investigation (written before tuning).
HELDOUT_IN = [
    "phone case", "iphone case", "laptop sleeve", "laptop bag", "ipad case", "earphone case",
    "camera bag", "dog jumper", "side table", "cushion cover", "blanket", "beach towel",
    "water bottle", "soft toy", "marker pen", "sewing kit", "lipstick", "nail polish", "keychain",
    "umbrella", "gift box", "baby sleeping bag", "sunglasses", "sports bra", "halloween costume",
    "something nice to wear to a wedding", "outfit for a beach holiday", "gift for my girlfriend",
    "cosy loungewear", "festival outfit", "clothes for a job interview", "what to wear to a party",
    "warm clothes for winter", "mickey mouse t-shirt", "gaming hoodie", "car coat",
]
HELDOUT_OOC = [
    "hair dryer", "smartwatch", "wireless mouse", "coffee maker", "electric toothbrush",
    "tennis racket", "bicycle helmet", "garden hose", "board game", "kitchen knife set",
    "led desk lamp", "baby stroller", "car seat for toddlers", "running treadmill",
    "vacuum cleaner", "gaming headset", "office desk", "protein bar", "cat litter",
    "iphone 15 pro", "samsung galaxy phone", "power bank", "dumbbells", "bookshelf",
]


def _is_ooc(row):
    # the 23 out_of_catalog queries plus the owner's b5 (gaming laptop)
    return bool(row.get("expect", {}).get("out_of_catalog")) or row["id"] == "b5"


def _rows():
    return [json.loads(line) for line in QUERIES.read_text(encoding="utf-8").splitlines() if line.strip()]


def eval_ooc_queries():
    return [r["query"] for r in _rows() if _is_ooc(r)]


def eval_in_catalogue_queries():
    return [r["query"] for r in _rows() if not _is_ooc(r)]


# ------------------------------------------------------------------ classifier

def test_all_24_eval_ooc_queries_are_detected():
    queries = eval_ooc_queries()
    assert len(queries) == 24
    missed = [q for q in queries if not classify(q).out_of_catalog]
    assert missed == []


def test_no_eval_in_catalogue_query_is_flagged():
    flagged = [q for q in eval_in_catalogue_queries() if classify(q).out_of_catalog]
    assert flagged == []


def test_heldout_in_catalogue_lookalikes_never_flagged():
    flagged = [q for q in HELDOUT_IN if classify(q).out_of_catalog]
    assert flagged == []


def test_heldout_ooc_recall_at_least_21_of_24():
    caught = [q for q in HELDOUT_OOC if classify(q).out_of_catalog]
    assert len(caught) >= 21, sorted(set(HELDOUT_OOC) - set(caught))


@pytest.mark.parametrize(
    "query, domain",
    [
        ("gaming laptop with RTX graphics", "electronics"),
        ("double door refrigerator", "appliances"),
        ("three seater sofa", "furniture"),
        ("whey protein powder", "food_health"),
        ("car tyres", "auto_tools"),
        ("acoustic guitar", "sport_music"),
    ],
)
def test_reason_values(query, domain):
    assert classify(query).reason == REASON_PREFIX + domain


def test_reason_values_are_a_fixed_set():
    valid = {REASON_PREFIX + d for d in UNSUPPORTED_DOMAINS}
    reasons = {classify(q).reason for q in eval_ooc_queries() + HELDOUT_OOC if classify(q).out_of_catalog}
    assert reasons <= valid


def test_in_catalogue_result_has_no_reason():
    result = classify("black dress")
    assert result.out_of_catalog is False and result.reason is None


# ------------------------------------------------------------------ traps

@pytest.mark.parametrize(
    "query",
    [
        # mouse
        "Mickey Mouse ears", "mickey mouse t-shirt", "minnie mouse pyjamas",
        "mouse print top", "mouse-themed clothing", "mouse",
        # bat
        "bat costume", "batwing dress", "batman t-shirt", "bat print clothing", "bat",
        # car vs cardigan
        "cardigan", "car coat", "race car costume",
        # catalogue protection
        "phone case", "laptop sleeve", "side table", "cushion cover", "keychain",
        "lipstick", "gift for my girlfriend", "festival outfit", "gaming hoodie",
        "camera bag", "laptop case", "phone strap", "headphone holder",
        # hosiery, not a garden hose
        "black hose",
        # empty / whitespace
        "", "   ",
    ],
)
def test_false_positive_traps_are_not_ooc(query):
    assert classify(query).out_of_catalog is False


@pytest.mark.parametrize(
    "query",
    ["computer mouse", "wireless mouse", "cricket bat", "baseball bat", "car tyres",
     "garden hose", "CRICKET BAT", "Wireless  Mouse"],
)
def test_full_unsupported_phrases_are_ooc(query):
    assert classify(query).out_of_catalog is True


def test_word_boundaries():
    assert classify("car").out_of_catalog is True
    assert classify("cardigan").out_of_catalog is False      # not "car"
    assert classify("batwing top").out_of_catalog is False    # not "bat"
    assert classify("laptops").out_of_catalog is True
    assert classify("desktop wallpaper").out_of_catalog is False  # "desk" inside a word


def test_deterministic():
    for q in eval_ooc_queries() + HELDOUT_IN:
        assert classify(q) == classify(q)


# ------------------------------------------------------------------ route

class SearchCalled(Exception):
    pass


@pytest.fixture
def route_env(monkeypatch):
    calls = []

    async def fake_search(query, top_k=20):
        calls.append(query)
        return [{
            "rank": 1, "article_id": "1", "distance": 0.5,
            "product": {"_id": "1", "name": "Dress", "product_type": "Dress",
                        "category": "Garment Full body", "department": "", "section": "",
                        "garment_group": "", "colour": "Black", "description": ""},
        }]

    monkeypatch.setattr(route, "semantic_search", fake_search)
    monkeypatch.setattr(route.intent_detector, "detect_intent",
                        lambda q: {"intent": "semantic_search", "confidence": 0.5})

    def set_flags(version="v2", ooc=True, kids=False, attr=False):
        monkeypatch.setattr(route.settings, "search_rerank_version", version)
        monkeypatch.setattr(route.settings, "search_v2_out_of_catalog", ooc)
        monkeypatch.setattr(route.settings, "search_v2_kids_downrank", kids)
        monkeypatch.setattr(route.settings, "search_v2_attribute_boost", attr)

    return calls, set_flags


async def _search(query):
    return await route.search_products(route.SearchRequest(query=query, top_k=10))


async def test_ooc_query_skips_faiss_and_returns_fields(route_env):
    calls, set_flags = route_env
    set_flags(ooc=True)
    resp = await _search("gaming laptop with RTX graphics")
    assert calls == []                                   # FAISS never called
    assert resp["products"] == [] and resp["count"] == 0
    assert resp["out_of_catalog"] is True
    assert resp["ooc_reason"] == "unsupported_domain:electronics"
    assert resp["rerank_version"] == "v2"


async def test_ooc_check_runs_before_recommendation_branch(route_env, monkeypatch):
    calls, set_flags = route_env
    set_flags(ooc=True)
    monkeypatch.setattr(route.intent_detector, "detect_intent",
                        lambda q: {"intent": "recommendation", "confidence": 0.9})

    async def fail(*a, **k):
        raise AssertionError("recommendation engine must not run for OOC queries")

    monkeypatch.setattr(route.recommendation_engine, "recommend", fail)
    resp = await _search("recommend a laptop")
    assert resp["out_of_catalog"] is True


async def test_normal_query_uses_existing_pipeline_without_new_fields(route_env):
    calls, set_flags = route_env
    set_flags(ooc=True)
    resp = await _search("black dress")
    assert calls == ["black dress"]
    assert "out_of_catalog" not in resp and "ooc_reason" not in resp
    assert resp["count"] == 1


@pytest.mark.parametrize("kids, attr", [(False, False), (True, False), (False, True), (True, True)])
async def test_flag_off_is_unchanged_for_every_s3_s4_combination(route_env, kids, attr):
    calls, set_flags = route_env
    set_flags(ooc=False, kids=kids, attr=attr)
    resp = await _search("gaming laptop with RTX graphics")
    assert calls == ["gaming laptop with RTX graphics"]  # normal search
    assert "out_of_catalog" not in resp and "ooc_reason" not in resp
    assert route.active_reranker() is route._V2_RERANKERS[(kids, attr)]


@pytest.mark.parametrize("kids, attr", [(False, False), (True, True)])
async def test_s3_s4_flags_independent_of_ooc(route_env, kids, attr):
    calls, set_flags = route_env
    set_flags(ooc=True, kids=kids, attr=attr)
    assert route.active_reranker() is route._V2_RERANKERS[(kids, attr)]
    resp = await _search("black dress")
    assert calls == ["black dress"] and "out_of_catalog" not in resp


async def test_v1_ignores_ooc_flag(route_env):
    calls, set_flags = route_env
    set_flags(version="v1", ooc=True, kids=True, attr=True)
    resp = await _search("gaming laptop with RTX graphics")
    assert calls == ["gaming laptop with RTX graphics"]
    assert "out_of_catalog" not in resp and "rerank_version" not in resp
    assert route.active_reranker() is route.reranker
    assert type(route.reranker) is SemanticReranker


async def test_ooc_response_keeps_existing_keys(route_env):
    calls, set_flags = route_env
    set_flags(ooc=False)
    normal = await _search("black dress")
    set_flags(ooc=True)
    ooc = await _search("air fryer")
    assert set(normal) <= set(ooc)                       # additive only
    assert set(ooc) - set(normal) == {"out_of_catalog", "ooc_reason"}


# ------------------------------------------------------------------ flag

@pytest.fixture
def no_env(monkeypatch):
    monkeypatch.delenv("SEARCH_V2_OUT_OF_CATALOG", raising=False)
    monkeypatch.delenv("SEARCH_RERANK_VERSION", raising=False)


def test_flag_default_false(no_env):
    s = Settings(_env_file=None)
    assert s.search_v2_out_of_catalog is False and s.search_rerank_version == "v1"


def test_flag_from_environment(no_env, monkeypatch):
    monkeypatch.setenv("SEARCH_V2_OUT_OF_CATALOG", "true")
    assert Settings(_env_file=None).search_v2_out_of_catalog is True
