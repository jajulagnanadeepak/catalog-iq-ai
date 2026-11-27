"""Health probes and search-unavailable handling (C-01, H-13).

The app is exercised over ASGI without running the lifespan, so no MongoDB
connection or model load happens.
"""

import httpx
import pytest

import main
import search


@pytest.fixture
def client():
    transport = httpx.ASGITransport(app=main.app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def healthy_db(monkeypatch, fake_db_cls, fake_collection_cls):
    db = fake_db_cls({"catalog_products": fake_collection_cls([{"_id": "1"}, {"_id": "2"}])})
    monkeypatch.setattr(main, "get_database", lambda: db)
    return db


@pytest.fixture
def ready_engine(monkeypatch, fake_index_cls, fake_model):
    engine = search.SearchEngine(
        model=fake_model,
        index=fake_index_cls(ntotal=2, results=([], [])),
        product_ids=["1", "2"],
    )
    monkeypatch.setattr(main, "get_search_engine", lambda: engine)
    return engine


async def test_legacy_health_unchanged(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "version": main.app.version}


async def test_live(client):
    r = await client.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_ready_when_all_dependencies_ok(client, healthy_db, ready_engine):
    r = await client.get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["checks"]["mongodb"]["catalog_products"] == 2
    assert body["checks"]["semantic_search"]["vectors"] == 2


async def test_not_ready_when_search_missing(client, healthy_db, isolated_search, monkeypatch):
    isolated_search.load_search_engine()
    monkeypatch.setattr(main, "get_search_engine", isolated_search.get_search_engine)

    r = await client.get("/health/ready")

    assert r.status_code == 503
    check = r.json()["checks"]["semantic_search"]
    assert check["ok"] is False
    assert "missing.index" in check["error"]


async def test_not_ready_when_mongo_down_and_no_details_leaked(
    client, monkeypatch, fake_db_cls, ready_engine
):
    secret_url = "mongodb+srv://user:hunter2@cluster.example"
    db = fake_db_cls(ping_error=RuntimeError(f"cannot reach {secret_url}"))
    monkeypatch.setattr(main, "get_database", lambda: db)

    r = await client.get("/health/ready")

    assert r.status_code == 503
    assert r.json()["checks"]["mongodb"] == {"ok": False, "error": "RuntimeError"}
    assert "hunter2" not in r.text


async def test_empty_catalog_warns(client, monkeypatch, fake_db_cls, ready_engine):
    monkeypatch.setattr(main, "get_database", lambda: fake_db_cls())
    r = await client.get("/health/ready")
    assert "DATABASE_NAME" in r.json()["checks"]["mongodb"]["warning"]


async def test_semantic_search_returns_503_when_index_missing(client, isolated_search):
    r = await client.post("/api/semantic-search", json={"query": "black dress"})
    assert r.status_code == 503
    assert r.json() == {"detail": "Semantic search is temporarily unavailable."}
