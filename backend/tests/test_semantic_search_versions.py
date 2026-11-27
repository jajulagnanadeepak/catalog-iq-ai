"""SEARCH_RERANK_VERSION selection: default v1, v2 only when set, v1 unchanged."""

import pytest
from pydantic import ValidationError

import routes.semantic_search as route
from config import Settings
from services.semantic_reranker import SemanticReranker
from services.semantic_reranker_v2 import SemanticRerankerV2


@pytest.fixture(autouse=True)
def no_env_flag(monkeypatch):
    monkeypatch.delenv("SEARCH_RERANK_VERSION", raising=False)


def test_default_is_v1():
    assert Settings(_env_file=None).search_rerank_version == "v1"


def test_v2_from_environment(monkeypatch):
    monkeypatch.setenv("SEARCH_RERANK_VERSION", "v2")
    assert Settings(_env_file=None).search_rerank_version == "v2"


@pytest.mark.parametrize("bad", ["v3", "V2 ", "latest", ""])
def test_invalid_version_fails_at_startup(monkeypatch, bad):
    monkeypatch.setenv("SEARCH_RERANK_VERSION", bad)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_v1_reranker_is_the_unmodified_class():
    assert type(route.reranker) is SemanticReranker
    assert type(route.reranker_v2) is SemanticRerankerV2


def _product(aid, name, ptype, group, distance):
    return {
        "rank": 1, "article_id": aid, "distance": distance,
        "product": {"_id": aid, "name": name, "product_type": ptype, "category": group,
                    "department": "", "section": "", "garment_group": "", "colour": "Black",
                    "description": ""},
    }


CANDIDATES = [
    _product("1", "A", "Dress", "Garment Full body", 0.2),
    _product("2", "B", "Top", "Garment Upper body", 0.3),
    _product("3", "C", "Dress", "Garment Full body", 0.4),
]


@pytest.fixture
def stub_search(monkeypatch):
    async def fake_semantic_search(query, top_k=20):
        return [dict(c, product=dict(c["product"])) for c in CANDIDATES]

    monkeypatch.setattr(route, "semantic_search", fake_semantic_search)
    monkeypatch.setattr(route.intent_detector, "detect_intent",
                        lambda q: {"intent": "semantic_search", "confidence": 0.5})


async def test_route_uses_v1_by_default_and_response_is_unchanged(stub_search, monkeypatch):
    monkeypatch.setattr(route.settings, "search_rerank_version", "v1")
    resp = await route.search_products(route.SearchRequest(query="black dress", top_k=5))
    assert set(resp) == {"success", "intent", "session_intent", "retrieved_candidates",
                         "count", "products"}
    assert "rerank_version" not in resp
    expected = SemanticReranker().rerank("black dress", CANDIDATES, limit=5)
    assert [p["article_id"] for p in resp["products"]] == [p["article_id"] for p in expected]


async def test_route_uses_v2_when_flag_set(stub_search, monkeypatch):
    monkeypatch.setattr(route.settings, "search_rerank_version", "v2")
    resp = await route.search_products(route.SearchRequest(query="black dress", top_k=5))
    assert resp["rerank_version"] == "v2"
    assert [p["product"]["product_type"] for p in resp["products"]] == ["Dress", "Dress"]
