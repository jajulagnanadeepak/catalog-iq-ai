"""WS-E3.3: safety of ``create_hm_embeddings.py`` (builds the live search artefacts).

Nothing real is used: the database functions are in-memory fakes, the
SentenceTransformer is a deterministic fake (no model download), settings are
patched, and real FAISS only reads and writes files inside ``tmp_path``.
"""

import importlib.util
import pickle
from pathlib import Path

import faiss
import numpy as np
import pytest
from pymongo.errors import ServerSelectionTimeoutError

import create_hm_embeddings as hm
import database.connection
import search

FAKE_URI = "mongodb+srv://fixture-user:Fixture-S3cret-PW@cluster.example.test/db"
SECRET_PARTS = ["Fixture-S3cret-PW", "fixture-user", "cluster.example.test", FAKE_URI]
DIM = 8

FIELDS = ["name", "product_type", "category", "department", "section", "garment_group",
          "colour", "description"]


def make_doc(i, **overrides):
    doc = {"_id": f"01000000{i:02d}", "article_id": f"01000000{i:02d}"}
    doc.update({f: f"{f}-{i}" for f in FIELDS})
    doc.update(overrides)
    return doc


# Deliberately not in _id order: the script must sort by _id.
DOCS = [make_doc(3), make_doc(1), make_doc(5), make_doc(2), make_doc(4)]
SORTED_IDS = [f"01000000{i:02d}" for i in range(1, 6)]


def fake_vectors(texts):
    """Deterministic float64 vectors (the script must cast to float32)."""
    return np.array(
        [[float(len(t)), float(i)] + [float((i + 1) * (k + 1)) for k in range(DIM - 2)]
         for i, t in enumerate(texts)],
        dtype=np.float64,
    )


def write_pair(index_path, ids_path, n, dim=DIM):
    index = faiss.IndexFlatL2(dim)
    if n:
        index.add(np.arange(n * dim, dtype=np.float32).reshape(n, dim))
    faiss.write_index(index, str(index_path))
    with open(ids_path, "wb") as f:
        pickle.dump([f"old-{i}" for i in range(n)], f)


def read_bytes(*paths):
    return [Path(p).read_bytes() for p in paths]


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeCursor:
    def __init__(self, env, docs):
        self.env, self.docs = env, docs

    def sort(self, key, direction):
        self.env.sorts.append((key, direction))
        self.docs = sorted(self.docs, key=lambda d: d[key], reverse=direction < 0)
        return self

    async def to_list(self, length=None):
        if self.env.find_error:
            raise self.env.find_error
        return [dict(d) for d in self.docs]


class FakeCollection:
    def __init__(self, env):
        self.env = env

    async def count_documents(self, query):
        self.env.counts += 1
        return self.env.count_override if self.env.count_override is not None else len(self.env.docs)

    def find(self, query, projection):
        self.env.finds.append((query, projection))
        return FakeCursor(self.env, self.env.docs)


class FakeModel:
    def __init__(self, env, name):
        self.env = env
        env.models.append(name)

    def encode(self, texts, **kwargs):
        self.env.encodes.append((list(texts), kwargs))
        if self.env.encode_error:
            raise self.env.encode_error
        return fake_vectors(texts)


class Env:
    def __init__(self, monkeypatch, tmp_path):
        self.mp = monkeypatch
        self.dir = tmp_path / "artifacts"
        self.dir.mkdir()
        self.index = self.dir / "hm_products.index"
        self.ids = self.dir / "hm_product_ids.pkl"
        self.docs = [dict(d) for d in DOCS]
        self.count_override = None
        self.counts = 0
        self.finds, self.sorts, self.models, self.encodes = [], [], [], []
        self.connects = self.closes = 0
        self.accessed = []
        self.connect_error = self.find_error = self.encode_error = None

        monkeypatch.setattr(hm, "INDEX_PATH", self.index)
        monkeypatch.setattr(hm, "IDS_PATH", self.ids)
        monkeypatch.setattr(hm.settings, "app_env", "development")
        monkeypatch.setattr(hm.settings, "mongodb_url", FAKE_URI)
        monkeypatch.setattr(hm, "SentenceTransformer", lambda name: FakeModel(self, name))

        async def connect_db():
            self.connects += 1
            if self.connect_error:
                raise self.connect_error

        async def close_db():
            self.closes += 1

        def get_database():
            env = self

            class FakeDB:
                def __getitem__(self, name):
                    env.accessed.append(name)
                    return FakeCollection(env)

            return FakeDB()

        monkeypatch.setattr(hm, "connect_db", connect_db)
        monkeypatch.setattr(hm, "close_db", close_db)
        monkeypatch.setattr(hm, "get_database", get_database)

    def old_pair(self, n=3):
        write_pair(self.index, self.ids, n)
        return read_bytes(self.index, self.ids)

    def files(self):
        return sorted(p.name for p in self.dir.iterdir())

    def production(self):
        self.mp.setattr(hm.settings, "app_env", "production")


@pytest.fixture
def env(monkeypatch, tmp_path):
    return Env(monkeypatch, tmp_path)


def run(argv):
    return hm.main(argv)


def assert_no_credentials(text):
    for part in SECRET_PARTS:
        assert part not in text


OVERWRITE = ["--apply", "--i-understand-this-overwrites-index"]


# ---------------------------------------------------------------------------
# Import safety and paths
# ---------------------------------------------------------------------------

def test_importing_has_no_side_effects(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("create_hm_embeddings must not do this at import time")

    import sentence_transformers
    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", forbidden)
    for name in ("connect_db", "get_database", "close_db"):
        monkeypatch.setattr(database.connection, name, forbidden)
    for name in ("read_index", "write_index"):
        monkeypatch.setattr(faiss, name, forbidden)

    spec = importlib.util.spec_from_file_location("hm_embeddings_under_test", Path(hm.__file__))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert callable(module.main)
    assert capsys.readouterr().out == ""


def test_artifact_paths_match_search_and_ignore_the_working_directory():
    here = Path(hm.__file__).resolve().parent
    assert hm.INDEX_PATH == here / "hm_products.index" == search.INDEX_PATH
    assert hm.IDS_PATH == here / "hm_product_ids.pkl" == search.IDS_PATH
    assert hm.MODEL_NAME == "all-MiniLM-L6-v2" == search.MODEL_NAME


def test_build_writes_to_the_artifact_directory_not_the_cwd(env, monkeypatch, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    assert run(["--apply"]) == hm.EXIT_OK

    assert env.files() == ["hm_product_ids.pkl", "hm_products.index"]
    assert list(elsewhere.iterdir()) == []


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------

def test_default_is_a_dry_run_without_model_or_writes(env, capsys):
    assert run([]) == hm.EXIT_OK

    assert env.models == [] and env.encodes == []
    assert env.finds == []          # read-only count only
    assert env.counts == 1
    assert env.files() == []        # nothing written
    out = capsys.readouterr().out
    for expected in [
        f"Target directory  : {env.dir}",
        "Model             : all-MiniLM-L6-v2",
        "Encode batch size : 64",
        "Catalogue count   : 5",
        "(missing)",
        "pair: none",
        "move the new pair into place (no existing artefacts)",
        "DRY RUN: nothing was changed",
    ]:
        assert expected in out
    assert_no_credentials(out)


def test_dry_run_inspects_an_existing_pair_read_only(env, capsys):
    before = env.old_pair(3)

    assert run([]) == hm.EXIT_OK

    assert read_bytes(env.index, env.ids) == before
    assert env.files() == ["hm_product_ids.pkl", "hm_products.index"]
    out = capsys.readouterr().out
    assert f"ntotal=3, dimension={DIM}" in out and "ids=3" in out
    assert "bytes, modified " in out
    assert "pair: consistent" in out
    assert "needs --i-understand-this-overwrites-index" in out


def test_dry_run_reports_a_mismatched_or_unreadable_pair(env, capsys):
    write_pair(env.index, env.ids, 3)
    with open(env.ids, "wb") as f:
        pickle.dump(["a", "b"], f)

    run([])
    assert "pair: MISMATCH" in capsys.readouterr().out

    env.index.write_bytes(b"not a faiss index")
    run([])
    out = capsys.readouterr().out
    assert "UNREADABLE" in out and "pair: INCOMPLETE or UNREADABLE" in out


# ---------------------------------------------------------------------------
# First build: generation logic unchanged
# ---------------------------------------------------------------------------

def test_first_build_preserves_generation_logic(env, capsys):
    env.docs[0].pop("colour")  # a missing field becomes "" via product.get(f, "")

    assert run(["--apply"]) == hm.EXIT_OK

    assert env.models == ["all-MiniLM-L6-v2"]
    assert env.accessed == ["catalog_products"]
    query, projection = env.finds[0]
    assert query == {} and projection == {f: 1 for f in ["_id", "article_id"] + FIELDS}
    assert env.sorts == [("_id", 1)]

    texts, kwargs = env.encodes[0]
    assert kwargs == {"convert_to_numpy": True, "show_progress_bar": True, "batch_size": 64}
    by_id = {d["_id"]: d for d in env.docs}
    expected_texts = [" ".join(str(by_id[i].get(f, "")) for f in FIELDS) for i in SORTED_IDS]
    assert texts == expected_texts
    assert " colour-3 " not in texts[2] and "garment_group-3  description-3" in texts[2]

    index = faiss.read_index(str(env.index))
    assert isinstance(index, faiss.IndexFlatL2)
    assert index.ntotal == 5 and index.d == DIM
    expected = fake_vectors(expected_texts).astype(np.float32)
    assert np.array_equal(np.vstack([index.reconstruct(i) for i in range(5)]), expected)

    with open(env.ids, "rb") as f:
        assert pickle.load(f) == SORTED_IDS   # plain list, sorted by _id

    assert env.files() == ["hm_product_ids.pkl", "hm_products.index"]  # no .tmp / .bak
    out = capsys.readouterr().out
    assert "First 5 mappings:" in out
    for i, article_id in enumerate(SORTED_IDS):
        assert f"FAISS {i} -> article_id {article_id}" in out
    assert "H&M FAISS INDEX COMPLETE" in out
    assert_no_credentials(out)


def test_catalogue_smaller_than_five_builds_and_prints_existing_mappings(env, capsys):
    env.docs = [make_doc(2), make_doc(1)]

    assert run(["--apply"]) == hm.EXIT_OK

    out = capsys.readouterr().out
    assert "FAISS 0 -> article_id 0100000001" in out
    assert "FAISS 1 -> article_id 0100000002" in out
    assert "FAISS 2 ->" not in out
    assert "H&M FAISS INDEX COMPLETE" in out
    assert faiss.read_index(str(env.index)).ntotal == 2


# ---------------------------------------------------------------------------
# Overwrite confirmation and rebuild
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("which", ["both", "index-only", "ids-only"])
def test_apply_refuses_to_overwrite_without_confirmation(env, capsys, which):
    env.old_pair(3)
    if which == "index-only":
        env.ids.unlink()
    elif which == "ids-only":
        env.index.unlink()
    before = {p.name: p.read_bytes() for p in env.dir.iterdir()}

    assert run(["--apply"]) == hm.EXIT_REFUSED

    assert {p.name: p.read_bytes() for p in env.dir.iterdir()} == before
    assert env.connects == 0 and env.models == []
    assert "--i-understand-this-overwrites-index" in capsys.readouterr().out


def test_overwrite_confirmation_without_apply_is_refused(env, capsys):
    before = env.old_pair(3)

    assert run(["--i-understand-this-overwrites-index"]) == hm.EXIT_REFUSED

    assert read_bytes(env.index, env.ids) == before
    assert env.connects == 0
    assert "has no effect without --apply" in capsys.readouterr().out


def test_rebuild_replaces_the_pair_and_keeps_the_previous_one_as_bak(env, capsys):
    old_index, old_ids = env.old_pair(3)

    assert run(OVERWRITE) == hm.EXIT_OK

    assert env.files() == ["hm_product_ids.pkl", "hm_product_ids.pkl.bak",
                           "hm_products.index", "hm_products.index.bak"]
    assert read_bytes(_bak(env.index), _bak(env.ids)) == [old_index, old_ids]
    assert faiss.read_index(str(env.index)).ntotal == 5
    with open(env.ids, "rb") as f:
        assert pickle.load(f) == SORTED_IDS
    assert "Previous pair kept as *.bak" in capsys.readouterr().out


def test_rebuild_drops_a_stale_backup_of_a_missing_artifact(env):
    env.old_pair(3)
    old_index = env.index.read_bytes()
    env.ids.unlink()
    _bak(env.ids).write_bytes(b"stale backup from an older run")

    assert run(OVERWRITE) == hm.EXIT_OK

    assert env.files() == ["hm_product_ids.pkl", "hm_products.index", "hm_products.index.bak"]
    assert _bak(env.index).read_bytes() == old_index


def _bak(path):
    return path.with_name(path.name + ".bak")


def _tmp(path):
    return path.with_name(path.name + ".tmp")


# ---------------------------------------------------------------------------
# Failures before promotion leave the live pair untouched
# ---------------------------------------------------------------------------

def test_encoding_failure_leaves_live_pair_untouched(env, capsys):
    before = env.old_pair(3)
    env.encode_error = RuntimeError(f"boom {FAKE_URI}")

    assert run(OVERWRITE) == hm.EXIT_ERROR

    assert read_bytes(env.index, env.ids) == before
    assert env.files() == ["hm_product_ids.pkl", "hm_products.index"]
    out = capsys.readouterr().out
    assert "ERROR during embedding generation (RuntimeError). Live artefacts were not changed." in out
    assert_no_credentials(out)


def test_write_failure_cleans_temporary_files(env, monkeypatch):
    before = env.old_pair(3)

    def failing_write_ids(ids, path):
        Path(path).write_bytes(b"partial")
        raise OSError("disk full")

    monkeypatch.setattr(hm, "_write_ids", failing_write_ids)

    assert run(OVERWRITE) == hm.EXIT_ERROR

    assert read_bytes(env.index, env.ids) == before
    assert env.files() == ["hm_product_ids.pkl", "hm_products.index"]


@pytest.mark.parametrize("corruption", ["ids-order", "ids-missing", "ntotal", "dimension"])
def test_validation_failure_leaves_live_pair_untouched(env, monkeypatch, capsys, corruption):
    before = env.old_pair(3)
    real_write_ids, real_write_index = hm._write_ids, hm._write_index

    if corruption == "ids-order":
        monkeypatch.setattr(hm, "_write_ids", lambda ids, p: real_write_ids(list(reversed(ids)), p))
    elif corruption == "ids-missing":
        monkeypatch.setattr(hm, "_write_ids", lambda ids, p: real_write_ids(ids[:-1], p))
    elif corruption == "ntotal":
        def short_index(index, p):
            smaller = faiss.IndexFlatL2(index.d)
            smaller.add(np.vstack([index.reconstruct(i) for i in range(index.ntotal - 1)]))
            real_write_index(smaller, p)
        monkeypatch.setattr(hm, "_write_index", short_index)
    else:
        def other_dim(index, p):
            wrong = faiss.IndexFlatL2(index.d + 1)
            wrong.add(np.zeros((index.ntotal, index.d + 1), dtype=np.float32))
            real_write_index(wrong, p)
        monkeypatch.setattr(hm, "_write_index", other_dim)

    assert run(OVERWRITE) == hm.EXIT_ERROR

    assert read_bytes(env.index, env.ids) == before
    assert env.files() == ["hm_product_ids.pkl", "hm_products.index"]
    assert "ERROR during temporary artefact validation" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Promotion failures: rollback
# ---------------------------------------------------------------------------

def failing_replace(monkeypatch, fail_calls):
    real = hm._replace
    calls = []

    def replace(src, dst):
        calls.append((Path(src).name, Path(dst).name))
        if len(calls) in fail_calls:
            raise PermissionError("file in use")
        real(src, dst)

    monkeypatch.setattr(hm, "_replace", replace)
    return calls


def test_promotion_failure_restores_and_verifies_the_previous_pair(env, monkeypatch, capsys):
    before = env.old_pair(3)
    # calls: 1 index->bak, 2 ids->bak, 3 tmp->index, 4 tmp->ids (fails), then restores
    calls = failing_replace(monkeypatch, fail_calls={4})

    assert run(OVERWRITE) == hm.EXIT_ERROR

    assert calls[:4] == [
        ("hm_products.index", "hm_products.index.bak"),
        ("hm_product_ids.pkl", "hm_product_ids.pkl.bak"),
        ("hm_products.index.tmp", "hm_products.index"),
        ("hm_product_ids.pkl.tmp", "hm_product_ids.pkl"),
    ]
    assert read_bytes(env.index, env.ids) == before
    assert env.files() == ["hm_product_ids.pkl", "hm_products.index"]  # temps cleaned
    assert "The previous artefacts were restored and verified." in capsys.readouterr().out


def test_first_build_promotion_failure_leaves_no_half_pair(env, monkeypatch):
    failing_replace(monkeypatch, fail_calls={2})  # 1 tmp->index, 2 tmp->ids (fails)

    assert run(["--apply"]) == hm.EXIT_ERROR

    assert env.files() == []


def test_rollback_failure_is_reported_and_temporary_files_are_kept(env, monkeypatch, capsys):
    env.old_pair(3)
    failing_replace(monkeypatch, fail_calls=set(range(4, 20)))  # promotion and restores fail

    assert run(OVERWRITE) == hm.EXIT_ROLLBACK_FAILED

    out = capsys.readouterr().out
    assert "ROLLBACK FAILED" in out and "Recover manually" in out
    assert _tmp(env.ids).exists()           # kept for manual recovery
    assert _bak(env.index).exists() and _bak(env.ids).exists()


# ---------------------------------------------------------------------------
# Production gate
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("argv", [[], ["--apply"], OVERWRITE], ids=["none", "apply", "apply+overwrite"])
@pytest.mark.parametrize("app_env", ["production", "PRODUCTION", " Production "])
def test_production_refuses_without_allow_production(env, monkeypatch, capsys, argv, app_env):
    before = env.old_pair(3)
    monkeypatch.setattr(hm.settings, "app_env", app_env)

    assert run(argv) == hm.EXIT_REFUSED

    assert env.connects == 0 and env.models == []
    assert read_bytes(env.index, env.ids) == before
    assert "REFUSED: APP_ENV=production" in capsys.readouterr().out


def test_production_with_allow_still_requires_every_other_flag(env):
    before = env.old_pair(3)
    env.production()

    assert run(["--allow-production"]) == hm.EXIT_OK                  # dry run only
    assert run(["--allow-production", "--apply"]) == hm.EXIT_REFUSED  # overwrite flag missing
    assert run(["--allow-production", "--i-understand-this-overwrites-index"]) == hm.EXIT_REFUSED
    assert read_bytes(env.index, env.ids) == before and env.models == []

    assert run(["--allow-production"] + OVERWRITE) == hm.EXIT_OK
    assert faiss.read_index(str(env.index)).ntotal == 5


# ---------------------------------------------------------------------------
# Invalid catalogue data: stopped before the model is loaded
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "mutate,message",
    [
        (lambda e: setattr(e, "docs", []), "catalog_products is empty"),
        (lambda e: e.docs[1].pop("article_id"), "has no article_id"),
        (lambda e: e.docs[1].update(article_id="  "), "has no article_id"),
        (lambda e: e.docs[1].update(article_id=None), "has no article_id"),
        (lambda e: e.docs[1].update(article_id=e.docs[0]["article_id"]), "Duplicate article_id"),
        (lambda e: setattr(e, "count_override", 6), "catalogue changed while reading"),
    ],
    ids=["empty", "missing-id", "blank-id", "none-id", "duplicate-id", "count-changed"],
)
def test_invalid_catalogue_stops_before_the_model(env, capsys, mutate, message):
    mutate(env)

    assert run(["--apply"]) == hm.EXIT_ERROR

    assert env.models == [] and env.encodes == []
    assert env.files() == []
    out = capsys.readouterr().out
    assert message in out and "Live artefacts were not changed" in out


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

def test_connection_error_does_not_print_credentials(env, capsys):
    env.connect_error = ServerSelectionTimeoutError(f"could not reach {FAKE_URI}")

    assert run([]) == hm.EXIT_ERROR

    out = capsys.readouterr().out
    assert "ServerSelectionTimeoutError" in out
    assert_no_credentials(out)


def test_database_error_while_reading_does_not_print_credentials(env, capsys):
    env.find_error = ServerSelectionTimeoutError(f"lost {FAKE_URI}")

    assert run(["--apply"]) == hm.EXIT_ERROR

    out = capsys.readouterr().out
    assert "ERROR during catalogue read (ServerSelectionTimeoutError)" in out
    assert_no_credentials(out)
    assert env.closes == 1
