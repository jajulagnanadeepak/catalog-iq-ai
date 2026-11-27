"""S10: the recommendation intent returned zero results.

``search.semantic_search()`` returns wrappers
``{"rank", "article_id", "distance", "product": {...}}``, but
``RecommendationEngine.recommend()`` read ``name``/``category`` from the
wrapper, so every candidate had an empty name and was skipped.

No MongoDB, network or real index: retrieval is replaced by in-memory fakes.
"""

import copy
from types import SimpleNamespace

import pytest

import ai.recommendation_engine as rec_module
import routes.semantic_search as route
import search
from ai.recommendation_engine import RecommendationEngine

S10_QUERIES = [
    "best black jeans",
    "recommend a summer dress",
    "suggest white sneakers for men",
    "popular hoodies",
    "best winter jacket for women",
    "recommend a black handbag",
]

# catalog_products-shaped fixture documents (not real catalogue data)
DOCS = [
    {"_id": "0100000001", "name": "Slim Black Jeans", "category": "Garment Lower body",
     "product_type": "Trousers", "colour": "Black", "section": "Womens Casual",
     "description": "Black denim jeans"},
    {"_id": "0100000002", "name": "Summer Midi Dress", "category": "Garment Full body",
     "product_type": "Dress", "colour": "Light Beige", "section": "Womens Casual",
     "description": "Light summer dress"},
    {"_id": "0100000003", "name": "White Sneakers", "category": "Shoes",
     "product_type": "Sneakers", "colour": "White", "section": "Men Shoes",
     "description": "Leather sneakers"},
    {"_id": "0100000004", "name": "Oversized Hoodie", "category": "Garment Upper body",
     "product_type": "Hoodie", "colour": "Grey", "section": "Divided",
     "description": "Hoodie"},
    {"_id": "0100000005", "name": "Padded Winter Jacket", "category": "Garment Upper body",
     "product_type": "Jacket", "colour": "Black", "section": "Womens Outerwear",
     "description": "Warm jacket"},
    {"_id": "0100000006", "name": "Black Shoulder Bag", "category": "Accessories",
     "product_type": "Bag", "colour": "Black", "section": "Womens Accessories",
     "description": "Leather handbag"},
]


def wrap(product, rank=1):
    """A result in the exact shape search.semantic_search() returns."""
    return {
        "rank": rank,
        "article_id": product.get("_id", f"id-{rank}"),
        "distance": 0.1 * rank,
        "product": product,
    }


@pytest.fixture
def fake_retrieval(monkeypatch):
    """Replace retrieval inside the engine with a fixed result list."""
    state = SimpleNamespace(results=[], calls=[])

    async def fake_semantic_search(query, top_k=20):
        state.calls.append((query, top_k))
        return state.results

    monkeypatch.setattr(rec_module, "semantic_search", fake_semantic_search)
    return state


async def recommend(query="best black jeans", limit=10):
    return await RecommendationEngine().recommend(query, limit=limit)


# ---------------------------------------------------------------------------
# Nested wrappers (the S10 regression)
# ---------------------------------------------------------------------------

async def test_nested_wrappers_return_recommendations(fake_retrieval):
    fake_retrieval.results = [wrap(dict(d), rank=i) for i, d in enumerate(DOCS, start=1)]

    out = await recommend()

    assert len(out) == len(DOCS)
    assert fake_retrieval.calls == [("best black jeans", 20)]  # retrieval call unchanged


async def test_name_and_category_are_read_from_the_nested_product(fake_retrieval):
    fake_retrieval.results = [
        wrap({"_id": "a", "name": "Slim Black Jeans", "category": "Trousers"}, 1),
        wrap({"_id": "b", "name": "Plain Tee"}, 2),  # no category
    ]

    out = await recommend()

    assert [p["name"] for p in out] == ["Slim Black Jeans", "Plain Tee"]
    assert out[0]["category"] == "Trousers"
    assert out[0]["reason"] == (
        "Recommended because it matches your search in the Trousers category."
    )
    assert out[1]["reason"] == "Recommended based on semantic similarity to your search."


async def test_results_are_flat_products_in_search_order(fake_retrieval):
    fake_retrieval.results = [wrap(dict(d), rank=i) for i, d in enumerate(DOCS, start=1)]

    out = await recommend()

    assert [p["_id"] for p in out] == [d["_id"] for d in DOCS]
    assert all("product" not in p and "rank" not in p for p in out)


async def test_duplicate_names_are_removed_case_insensitively(fake_retrieval):
    fake_retrieval.results = [
        wrap({"_id": "1", "name": "Slim Black Jeans"}, 1),
        wrap({"_id": "2", "name": "slim black jeans"}, 2),
        wrap({"_id": "3", "name": "  SLIM BLACK JEANS  "}, 3),
        wrap({"_id": "4", "name": "Wide Jeans"}, 4),
    ]

    out = await recommend()

    assert [p["_id"] for p in out] == ["1", "4"]  # first occurrence wins


@pytest.mark.parametrize("limit,expected", [(1, 1), (3, 3), (6, 6), (10, 6), (0, 1), (-5, 1)])
async def test_limit_is_respected(fake_retrieval, limit, expected):
    fake_retrieval.results = [wrap(dict(d), rank=i) for i, d in enumerate(DOCS, start=1)]

    out = await recommend(limit=limit)

    # max(1, limit): unchanged existing behaviour
    assert len(out) == expected
    assert [p["_id"] for p in out] == [d["_id"] for d in DOCS[:expected]]


async def test_missing_fields_are_not_fabricated(fake_retrieval):
    product = {"_id": "a", "name": "Slim Black Jeans"}
    fake_retrieval.results = [wrap(product)]

    out = await recommend()

    assert set(out[0]) == {"_id", "name", "reason"}
    for field in ("price", "original_price", "rating", "reviews", "image", "brand",
                  "category", "article_id", "distance", "recommendation_score"):
        assert field not in out[0]


@pytest.mark.parametrize(
    "item",
    [
        {"rank": 1, "article_id": "x", "distance": 0.1, "product": None},
        {"rank": 1, "article_id": "x", "distance": 0.1, "product": "Slim Black Jeans"},
        {"rank": 1, "article_id": "x", "distance": 0.1, "product": ["Slim Black Jeans"]},
        {"rank": 1, "article_id": "x", "distance": 0.1, "product": 42},
        {"rank": 1, "article_id": "x", "distance": 0.1, "product": {}},
        {"rank": 1, "article_id": "x", "distance": 0.1},
        None,
        "Slim Black Jeans",
        42,
        ["Slim Black Jeans"],
    ],
    ids=["product-none", "product-str", "product-list", "product-int", "product-empty",
         "product-missing", "item-none", "item-str", "item-int", "item-list"],
)
async def test_missing_null_or_invalid_product_data_is_skipped(fake_retrieval, item):
    fake_retrieval.results = [item, wrap({"_id": "ok", "name": "Wide Jeans"}, 2)]

    out = await recommend()

    assert [p["_id"] for p in out] == ["ok"]


@pytest.mark.parametrize("name", ["", "   ", None, "\t\n"], ids=["empty", "spaces", "none", "whitespace"])
async def test_empty_names_are_skipped(fake_retrieval, name):
    fake_retrieval.results = [
        wrap({"_id": "blank", "name": name}, 1),
        wrap({"_id": "ok", "name": "Wide Jeans"}, 2),
    ]

    out = await recommend()

    assert [p["_id"] for p in out] == ["ok"]


async def test_missing_name_key_is_skipped(fake_retrieval):
    fake_retrieval.results = [wrap({"_id": "noname", "category": "Trousers"}, 1)]

    assert await recommend() == []


# ---------------------------------------------------------------------------
# Flat products (previous input shape) and edge cases
# ---------------------------------------------------------------------------

async def test_flat_product_dicts_are_still_supported(fake_retrieval):
    fake_retrieval.results = [
        {"_id": "f1", "name": "Slim Black Jeans", "category": "Trousers"},
        {"_id": "f2", "name": "Wide Jeans"},
    ]

    out = await recommend()

    assert [p["_id"] for p in out] == ["f1", "f2"]
    assert out[0]["reason"].endswith("in the Trousers category.")


async def test_flat_and_nested_results_can_be_mixed(fake_retrieval):
    fake_retrieval.results = [
        {"_id": "f1", "name": "Slim Black Jeans"},
        wrap({"_id": "n1", "name": "slim black jeans"}, 2),  # duplicate across shapes
        wrap({"_id": "n2", "name": "Wide Jeans"}, 3),
    ]

    out = await recommend()

    assert [p["_id"] for p in out] == ["f1", "n2"]


async def test_empty_search_results_return_empty_list(fake_retrieval):
    fake_retrieval.results = []

    assert await recommend() == []


async def test_input_objects_are_not_modified(fake_retrieval):
    results = [wrap(dict(d), rank=i) for i, d in enumerate(DOCS, start=1)]
    results.append({"_id": "f1", "name": "Flat Product", "category": "Trousers"})
    fake_retrieval.results = results
    before = copy.deepcopy(results)

    out = await recommend()

    assert results == before
    assert all("reason" not in r.get("product", r) for r in results)
    inputs = [r.get("product", r) for r in results]
    assert all(all(p is not src for src in inputs) for p in out)


# ---------------------------------------------------------------------------
# Real search.semantic_search output (contract) and the route (S10 queries)
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_catalog(monkeypatch, fake_index_cls, fake_model, fake_db_cls, fake_collection_cls):
    """Run the real search.semantic_search against an in-memory index and DB."""
    ids = [d["_id"] for d in DOCS]
    engine = SimpleNamespace(
        ready=True,
        index=fake_index_cls(len(ids), ([0.1 * i for i in range(len(ids))], list(range(len(ids))))),
        model=fake_model,
        product_ids=ids,
    )
    monkeypatch.setattr(search, "_ensure_ready", lambda: engine)
    monkeypatch.setattr(
        search,
        "get_database",
        lambda: fake_db_cls({"catalog_products": fake_collection_cls([dict(d) for d in DOCS])}),
    )


async def test_semantic_search_result_shape_contract(fake_catalog):
    # If this shape changes, recommend() must be updated with it.
    results = await search.semantic_search("best black jeans")

    assert results
    assert set(results[0]) == {"rank", "article_id", "distance", "product"}
    assert "name" not in results[0]
    assert results[0]["product"]["name"] == "Slim Black Jeans"


async def test_engine_with_real_semantic_search_output(fake_catalog):
    out = await recommend("best black jeans")

    assert [p["name"] for p in out] == [d["name"] for d in DOCS]
    assert out[0]["reason"] == (
        "Recommended because it matches your search in the Garment Lower body category."
    )


@pytest.fixture
def v1_route(monkeypatch, fake_catalog):
    """The semantic-search route with default (v1, all flags off) settings."""
    monkeypatch.setattr(route.settings, "search_rerank_version", "v1")
    monkeypatch.setattr(route.settings, "search_v2_out_of_catalog", False)
    monkeypatch.setattr(route.settings, "search_v2_kids_downrank", False)
    monkeypatch.setattr(route.settings, "search_v2_attribute_boost", False)


@pytest.mark.parametrize("query", S10_QUERIES)
async def test_s10_queries_return_recommendations_through_the_route(v1_route, query):
    resp = await route.search_products(route.SearchRequest(query=query))

    assert resp["intent"]["intent"] == "recommendation"  # real intent detector
    assert resp["count"] > 0
    assert resp["count"] == len(resp["products"])
    assert all(p["name"] and p["reason"] for p in resp["products"])
    # Response shape of the recommendation branch is unchanged.
    assert set(resp) == {"success", "intent", "session_intent", "count", "products"}
