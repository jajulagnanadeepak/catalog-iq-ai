"""Shared fixtures for the Phase 1 test suite.

These tests never touch MongoDB, the network, or the real FAISS index:
the database and search engine are replaced with small in-memory fakes.
"""

import pytest


class FakeIndex:
    """Minimal stand-in for a faiss.Index used by search.semantic_search."""

    def __init__(self, ntotal, results):
        self.ntotal = ntotal
        self._results = results  # (distances, indices)

    def search(self, query_embedding, top_k):
        import numpy as np

        distances, indices = self._results
        return (
            np.array([distances[:top_k]], dtype="float32"),
            np.array([indices[:top_k]], dtype="int64"),
        )


class FakeModel:
    def encode(self, texts, convert_to_numpy=True):
        import numpy as np

        return np.zeros((len(texts), 384), dtype="float32")


class FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, length=None):
        return list(self._docs)[:length] if length else list(self._docs)


class FakeCollection:
    def __init__(self, docs):
        self.docs = docs

    def find(self, query):
        wanted = set(query["_id"]["$in"])
        return FakeCursor([dict(d) for d in self.docs if d["_id"] in wanted])

    async def estimated_document_count(self):
        return len(self.docs)


class FakeDatabase:
    def __init__(self, collections=None, ping_error=None):
        self._collections = collections or {}
        self._ping_error = ping_error

    def __getitem__(self, name):
        return self._collections.setdefault(name, FakeCollection([]))

    async def command(self, name):
        if self._ping_error:
            raise self._ping_error
        return {"ok": 1}


@pytest.fixture
def fake_index_cls():
    return FakeIndex


@pytest.fixture
def fake_model():
    return FakeModel()


@pytest.fixture
def fake_db_cls():
    return FakeDatabase


@pytest.fixture
def fake_collection_cls():
    return FakeCollection


@pytest.fixture
def isolated_search(monkeypatch, tmp_path):
    """Reset the search engine singleton and point it at non-existent files."""
    import search

    monkeypatch.setattr(search, "_engine", search.SearchEngine())
    monkeypatch.setattr(search, "INDEX_PATH", tmp_path / "missing.index")
    monkeypatch.setattr(search, "IDS_PATH", tmp_path / "missing.pkl")
    return search
