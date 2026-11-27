"""Search engine lifecycle (C-01, H-07) and unchanged result behaviour."""

import pytest


async def test_import_does_not_load_model(isolated_search):
    # Importing the module must not load anything heavy.
    assert isolated_search.get_search_engine().ready is False


def test_missing_artefacts_reported_without_model_download(isolated_search, monkeypatch):
    import sys

    # If the loader tried to import/download the model this would blow up.
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)

    engine = isolated_search.load_search_engine()

    assert engine.ready is False
    assert "missing.index" in engine.error
    assert "create_hm_embeddings.py" in engine.error
    status = engine.status()
    assert status["ready"] is False and status["vectors"] == 0


async def test_semantic_search_raises_unavailable_when_not_loaded(isolated_search):
    with pytest.raises(isolated_search.SearchUnavailableError):
        await isolated_search.semantic_search("black dress", top_k=5)


async def test_empty_query_returns_empty_without_engine(isolated_search):
    assert await isolated_search.semantic_search("   ") == []


async def test_results_shape_and_ordering_unchanged(
    isolated_search, monkeypatch, fake_index_cls, fake_model, fake_db_cls, fake_collection_cls
):
    search = isolated_search
    ids = ["0001", "0002", "0003"]
    # FAISS may return -1 for empty slots; product 0003 is missing in Mongo.
    index = fake_index_cls(
        ntotal=3,
        results=([0.1, 0.2, 0.3, 9.9], [1, 0, 2, -1]),
    )
    monkeypatch.setattr(
        search,
        "_engine",
        search.SearchEngine(model=fake_model, index=index, product_ids=ids),
    )
    db = fake_db_cls(
        {
            "catalog_products": fake_collection_cls(
                [{"_id": "0001", "prod_name": "A"}, {"_id": "0002", "prod_name": "B"}]
            )
        }
    )
    monkeypatch.setattr(search, "get_database", lambda: db)

    results = await search.semantic_search("anything", top_k=10)

    # top_k is clamped to index size (3); -1 and missing products are skipped.
    assert [r["article_id"] for r in results] == ["0002", "0001"]
    assert results[0] == {
        "rank": 1,
        "article_id": "0002",
        "distance": pytest.approx(0.1),
        "product": {"_id": "0002", "prod_name": "B"},
    }
    assert results[1]["rank"] == 2


def test_engine_status_reports_counts(isolated_search, fake_index_cls, fake_model):
    engine = isolated_search.SearchEngine(
        model=fake_model,
        index=fake_index_cls(ntotal=2, results=([], [])),
        product_ids=["a", "b"],
    )
    assert engine.status()["ready"] is True
    assert engine.status()["vectors"] == 2
    assert engine.status()["product_ids"] == 2
