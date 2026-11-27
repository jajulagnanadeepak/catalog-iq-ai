"""WS-E3.1: safety of the repository-root ``seed.py`` (legacy Products seeder).

The real script is never executed against MongoDB here: every test loads the
module from its file path and passes a fake client factory; the CSV is a
temporary file and ``load_dotenv`` is replaced so no real ``.env`` is read.
"""

import importlib.util
from pathlib import Path

import pymongo
import pytest
from pymongo.errors import ServerSelectionTimeoutError

SEED_PATH = Path(__file__).resolve().parents[2] / "seed.py"

FAKE_URI = "mongodb+srv://fixture-user:Fixture-S3cret-PW@cluster.example.test/db"
SECRET_PARTS = ["Fixture-S3cret-PW", "fixture-user", "cluster.example.test", FAKE_URI]

CSV_TEXT = (
    "article_id,prod_name,product_type_name,product_group_name,department_name,"
    "section_name,garment_group_name,colour_group_name,detail_desc\n"
    "0100000001,Slim Jeans,Trousers,Garment Lower body,Denim,Womens Casual,"
    "Trousers Denim,Black,Black denim jeans\n"
    "0100000002,Midi Dress,Dress,Garment Full body,Dresses,Womens Casual,"
    "Dresses Ladies,Light Beige,\n"
)


def load_seed():
    spec = importlib.util.spec_from_file_location("root_seed_under_test", SEED_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeCollection:
    def __init__(self, existing=3):
        self.existing = existing
        self.calls = []

    def count_documents(self, query):
        self.calls.append(("count_documents", query))
        return self.existing

    def delete_many(self, query):
        self.calls.append(("delete_many", query))

    def insert_many(self, records):
        self.calls.append(("insert_many", [dict(r) for r in records]))

    def create_index(self, field, **kwargs):
        self.calls.append(("create_index", field, kwargs))

    @property
    def writes(self):
        return [c for c in self.calls if c[0] in ("delete_many", "insert_many", "create_index")]


class FakeAdmin:
    def __init__(self, client):
        self.client = client

    def command(self, name):
        self.client.calls.append(("admin.command", name))
        return {"ok": 1}


class FakeDatabase:
    def __init__(self, client, name):
        self.client, self.name = client, name

    def __getitem__(self, collection_name):
        self.client.accessed.append((self.name, collection_name))
        return self.client.collection


class FakeClient:
    def __init__(self, collection):
        self.collection = collection
        self.calls = []
        self.accessed = []
        self.admin = FakeAdmin(self)

    def __getitem__(self, db_name):
        return FakeDatabase(self, db_name)


@pytest.fixture
def env(monkeypatch, tmp_path):
    """Temporary CSV in the working directory, no real .env, fake client factory."""
    (tmp_path / "articles.csv").write_text(CSV_TEXT, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("MONGO_URI", FAKE_URI)

    seed = load_seed()
    monkeypatch.setattr(seed, "load_dotenv", lambda *a, **k: None)

    collection = FakeCollection()
    created = []

    def factory(uri):
        client = FakeClient(collection)
        created.append((uri, client))
        return client

    return seed, collection, created, factory


def assert_no_credentials(text):
    for part in SECRET_PARTS:
        assert part not in text


# ---------------------------------------------------------------------------
# Import safety
# ---------------------------------------------------------------------------

def test_importing_has_no_side_effects(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("seed.py must not do this at import time")

    monkeypatch.setattr(pymongo, "MongoClient", forbidden)
    monkeypatch.setattr("pandas.read_csv", forbidden)
    monkeypatch.setattr("dotenv.load_dotenv", forbidden)

    seed = load_seed()

    assert callable(seed.main)
    assert capsys.readouterr().out == ""


# ---------------------------------------------------------------------------
# Dry run (default)
# ---------------------------------------------------------------------------

def test_default_invocation_is_a_dry_run_with_no_writes(env, capsys):
    seed, collection, created, factory = env

    assert seed.main([], client_factory=factory) == seed.EXIT_OK

    assert collection.writes == []
    assert collection.calls == [("count_documents", {})]  # read-only
    out = capsys.readouterr().out
    assert "Target database   : CatalogIQ" in out
    assert "Target collection : Products" in out
    assert "CSV rows          : 2" in out
    assert "Existing documents: 3" in out
    assert "delete_many" in out and "insert_many: 2 documents" in out
    assert "product_id (unique)" in out
    assert "DRY RUN: nothing was changed" in out
    assert_no_credentials(out)


def test_dry_run_without_uri_reports_plan_and_never_connects(env, monkeypatch, capsys):
    seed, collection, created, factory = env
    monkeypatch.delenv("MONGO_URI")

    assert seed.main([], client_factory=factory) == seed.EXIT_OK

    assert created == []
    out = capsys.readouterr().out
    assert "Existing documents: unknown (MONGO_URI not set)" in out
    assert "DRY RUN" in out


# ---------------------------------------------------------------------------
# Confirmation flags
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "argv,missing",
    [(["--apply"], "--i-understand-this-deletes"), (["--i-understand-this-deletes"], "--apply")],
    ids=["apply-only", "confirm-only"],
)
def test_one_flag_without_the_other_refuses(env, capsys, argv, missing):
    seed, collection, created, factory = env

    assert seed.main(argv, client_factory=factory) == seed.EXIT_REFUSED

    assert created == []  # refused before connecting
    assert collection.calls == []
    out = capsys.readouterr().out
    assert "REFUSED" in out and f"missing {missing}" in out


def test_both_flags_run_the_unchanged_write_path(env, capsys):
    seed, collection, created, factory = env

    argv = ["--apply", "--i-understand-this-deletes"]
    assert seed.main(argv, client_factory=factory) == seed.EXIT_OK

    assert [uri for uri, _ in created] == [FAKE_URI]
    client = created[0][1]
    assert client.calls == [("admin.command", "ping")]
    assert set(client.accessed) == {("CatalogIQ", "Products")}

    names = [c[0] for c in collection.calls]
    assert names == ["count_documents", "delete_many", "insert_many"] + ["create_index"] * 5
    assert collection.calls[1] == ("delete_many", {})

    inserted = collection.calls[2][1]
    assert inserted == [
        {"product_id": "100000001", "name": "Slim Jeans", "product_type": "Trousers",
         "category": "Garment Lower body", "department": "Denim", "section": "Womens Casual",
         "garment_group": "Trousers Denim", "colour": "Black", "description": "Black denim jeans"},
        {"product_id": "100000002", "name": "Midi Dress", "product_type": "Dress",
         "category": "Garment Full body", "department": "Dresses", "section": "Womens Casual",
         "garment_group": "Dresses Ladies", "colour": "Light Beige", "description": ""},
    ]
    assert collection.calls[3:] == [
        ("create_index", "product_id", {"unique": True}),
        ("create_index", "name", {}),
        ("create_index", "category", {}),
        ("create_index", "department", {}),
        ("create_index", "colour", {}),
    ]
    out = capsys.readouterr().out
    assert "Successfully Imported 2 Products" in out
    assert_no_credentials(out)


def test_apply_without_uri_fails_without_connecting(env, monkeypatch, capsys):
    seed, collection, created, factory = env
    monkeypatch.delenv("MONGO_URI")

    argv = ["--apply", "--i-understand-this-deletes"]
    assert seed.main(argv, client_factory=factory) == seed.EXIT_ERROR

    assert created == [] and collection.calls == []
    assert "MONGO_URI not found" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Production
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "argv",
    [[], ["--apply"], ["--i-understand-this-deletes"], ["--apply", "--i-understand-this-deletes"]],
    ids=["no-flags", "apply", "confirm", "both-flags"],
)
@pytest.mark.parametrize("app_env", ["production", "PRODUCTION", " Production "])
def test_production_always_refuses(env, monkeypatch, capsys, argv, app_env):
    seed, collection, created, factory = env
    monkeypatch.setenv("APP_ENV", app_env)

    assert seed.main(argv, client_factory=factory) == seed.EXIT_REFUSED

    assert created == [] and collection.calls == []
    assert "REFUSED: APP_ENV=production" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

def test_connection_error_does_not_print_the_uri(env, capsys):
    seed, collection, created, factory = env

    def failing_factory(uri):
        raise ServerSelectionTimeoutError(f"could not reach {uri}")

    assert seed.main([], client_factory=failing_factory) == seed.EXIT_ERROR

    out = capsys.readouterr().out
    assert "ServerSelectionTimeoutError" in out
    assert_no_credentials(out)
    assert collection.calls == []
