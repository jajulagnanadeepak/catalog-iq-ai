"""WS-E3.6: safety of ``database/seed.py`` (the 12-product demo ``products`` seed).

MongoDB is never touched: ``connect_db`` / ``get_database`` / ``close_db`` are
replaced by in-memory fakes and settings are patched.
"""

import importlib.util
from pathlib import Path

import pytest
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError

import database.connection
import database.seed as seed_mod

MODULE_PATH = Path(seed_mod.__file__)

FAKE_URI = "mongodb+srv://fixture-user:Fixture-S3cret-PW@cluster.example.test/db"
SECRET_PARTS = ["Fixture-S3cret-PW", "fixture-user", "cluster.example.test", FAKE_URI]

EXPECTED_IDS = [f"p-{i:03d}" for i in range(1, 13)]


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeCollection:
    def __init__(self):
        self.docs = 0
        self.calls = []
        self.insert_error = None
        self.count_error = None

    async def count_documents(self, query):
        self.calls.append(("count_documents", query))
        if self.count_error:
            raise self.count_error
        return self.docs

    async def insert_many(self, docs, *args, **kwargs):
        if self.insert_error:
            raise self.insert_error
        self.calls.append(("insert_many", [dict(d) for d in docs]))
        self.docs += len(docs)

    def __getattr__(self, name):
        # Any other collection method (update/delete/replace/drop...) is a bug.
        raise AssertionError(f"seed must not call collection.{name}")

    @property
    def writes(self):
        return [c for c in self.calls if c[0] != "count_documents"]


class Env:
    def __init__(self, monkeypatch):
        self.collection = FakeCollection()
        self.connects = 0
        self.closes = 0
        self.accessed = []
        self.connect_error = None

        monkeypatch.setattr(seed_mod.settings, "app_env", "development")
        monkeypatch.setattr(seed_mod.settings, "database_name", "FixtureDB")
        monkeypatch.setattr(seed_mod.settings, "mongodb_url", FAKE_URI)

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
                    return env.collection

            return FakeDB()

        monkeypatch.setattr(seed_mod, "connect_db", connect_db)
        monkeypatch.setattr(seed_mod, "close_db", close_db)
        monkeypatch.setattr(seed_mod, "get_database", get_database)
        self.monkeypatch = monkeypatch

    def production(self, value="production"):
        self.monkeypatch.setattr(seed_mod.settings, "app_env", value)


@pytest.fixture
def env(monkeypatch):
    return Env(monkeypatch)


def run(argv):
    return seed_mod.main(argv)


def assert_no_credentials(text):
    for part in SECRET_PARTS:
        assert part not in text


# ---------------------------------------------------------------------------
# Import safety and data integrity
# ---------------------------------------------------------------------------

def test_importing_has_no_side_effects(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("database.seed must not do this at import time")

    monkeypatch.setattr(database.connection, "connect_db", forbidden)
    monkeypatch.setattr(database.connection, "get_database", forbidden)
    monkeypatch.setattr(database.connection, "close_db", forbidden)

    spec = importlib.util.spec_from_file_location("database_seed_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert callable(module.main)
    assert len(module.PRODUCTS) == 12
    assert capsys.readouterr().out == ""


def test_products_are_the_twelve_demo_items():
    ids = [p["_id"] for p in seed_mod.PRODUCTS]
    assert ids == EXPECTED_IDS
    for product in seed_mod.PRODUCTS:
        for field in ("name", "brand", "category", "price", "in_stock"):
            assert field in product, (product["_id"], field)
    assert seed_mod.COLLECTION_NAME == "products"


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------

def test_default_invocation_is_a_dry_run(env, capsys):
    assert run([]) == seed_mod.EXIT_OK

    out = capsys.readouterr().out
    for expected in [
        "Target database   : FixtureDB",
        "Target collection : products",
        "Existing documents: 0",
        "insert 12 demo products (p-001 to p-012)",
        "DRY RUN: nothing was changed",
    ]:
        assert expected in out
    assert env.collection.writes == []
    assert env.accessed == ["products"]
    assert env.closes == 1
    assert_no_credentials(out)


def test_dry_run_on_non_empty_collection_reports_skip(env, capsys):
    env.collection.docs = 5

    assert run([]) == seed_mod.EXIT_OK

    out = capsys.readouterr().out
    assert "Existing documents: 5" in out
    assert "Planned operation : none" in out
    assert "SKIPPED" in out
    assert env.collection.writes == []


# ---------------------------------------------------------------------------
# --apply
# ---------------------------------------------------------------------------

def test_apply_inserts_twelve_into_empty_collection(env, capsys):
    assert run(["--apply"]) == seed_mod.EXIT_OK

    writes = env.collection.writes
    assert len(writes) == 1
    op, docs = writes[0]
    assert op == "insert_many"
    assert [d["_id"] for d in docs] == EXPECTED_IDS
    assert docs == seed_mod.PRODUCTS
    assert env.closes == 1

    out = capsys.readouterr().out
    assert "Seeded 12 products into 'FixtureDB.products'." in out
    assert_no_credentials(out)


def test_apply_does_not_mutate_products_constant(env):
    before = [dict(p) for p in seed_mod.PRODUCTS]
    assert run(["--apply"]) == seed_mod.EXIT_OK
    assert seed_mod.PRODUCTS == before


def test_apply_on_non_empty_collection_changes_nothing(env, capsys):
    env.collection.docs = 1

    assert run(["--apply"]) == seed_mod.EXIT_OK

    assert env.collection.writes == []
    assert env.collection.docs == 1
    assert "SKIPPED" in capsys.readouterr().out
    assert env.closes == 1


def test_second_apply_is_a_no_op(env):
    assert run(["--apply"]) == seed_mod.EXIT_OK
    assert run(["--apply"]) == seed_mod.EXIT_OK
    assert len(env.collection.writes) == 1
    assert env.collection.docs == 12


# ---------------------------------------------------------------------------
# Production refusal
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("argv", [[], ["--apply"]])
@pytest.mark.parametrize("value", ["production", " Production "])
def test_production_is_refused_before_connecting(env, capsys, argv, value):
    env.production(value)

    assert run(argv) == seed_mod.EXIT_REFUSED

    assert env.connects == 0
    assert env.accessed == []
    assert env.collection.calls == []
    out = capsys.readouterr().out
    assert "REFUSED: APP_ENV=production" in out
    assert_no_credentials(out)


def test_there_is_no_production_override_flag(env):
    env.production()
    with pytest.raises(SystemExit) as exc:
        run(["--apply", "--allow-production"])
    assert exc.value.code != 0
    assert env.connects == 0


# ---------------------------------------------------------------------------
# Failures: non-zero exit, close_db guaranteed, no credentials printed
# ---------------------------------------------------------------------------

def test_connect_failure_exits_non_zero_without_credentials(env, capsys):
    env.connect_error = ServerSelectionTimeoutError(f"no servers at {FAKE_URI}")

    assert run(["--apply"]) == seed_mod.EXIT_ERROR

    assert env.collection.calls == []
    assert env.closes == 1
    out = capsys.readouterr().out
    assert "ServerSelectionTimeoutError" in out
    assert_no_credentials(out)


def test_count_failure_exits_non_zero_and_closes(env, capsys):
    env.collection.count_error = ServerSelectionTimeoutError(f"lost {FAKE_URI}")

    assert run([]) == seed_mod.EXIT_ERROR

    assert env.collection.writes == []
    assert env.closes == 1
    assert_no_credentials(capsys.readouterr().out)


def test_insert_failure_exits_non_zero_and_closes(env, capsys):
    env.collection.insert_error = DuplicateKeyError(f"E11000 dup key on {FAKE_URI}")

    assert run(["--apply"]) == seed_mod.EXIT_ERROR

    assert env.closes == 1
    out = capsys.readouterr().out
    assert "DuplicateKeyError" in out
    assert "check it before re-running" in out
    assert_no_credentials(out)


def test_unknown_flag_exits_non_zero_without_connecting(env):
    with pytest.raises(SystemExit) as exc:
        run(["--force"])
    assert exc.value.code != 0
    assert env.connects == 0


def test_successful_runs_never_print_credentials(env, capsys):
    run([])
    run(["--apply"])
    assert_no_credentials(capsys.readouterr().out)
