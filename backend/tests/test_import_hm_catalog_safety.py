"""WS-E3.2: safety of ``database/import_hm_catalog.py`` (replaces the live catalogue).

The real import is never executed against MongoDB: ``connect_db`` /
``get_database`` / ``close_db`` are replaced by in-memory fakes, the CSV is a
temporary file, ``input()`` is stubbed and settings are patched.
"""

import importlib.util
from pathlib import Path

import pytest
from pymongo.errors import AutoReconnect, ServerSelectionTimeoutError

import database.connection
import database.import_hm_catalog as hm

MODULE_PATH = Path(hm.__file__)

FAKE_URI = "mongodb+srv://fixture-user:Fixture-S3cret-PW@cluster.example.test/db"
SECRET_PARTS = ["Fixture-S3cret-PW", "fixture-user", "cluster.example.test", FAKE_URI]

HEADER = (
    "article_id,prod_name,product_type_name,product_group_name,department_name,"
    "section_name,garment_group_name,colour_group_name,detail_desc\n"
)


def csv_rows(n):
    return "".join(
        f"01000000{i:02d},Item {i},Trousers,Garment Lower body,Denim,Womens Casual,"
        f"Trousers Denim,Black,Description {i}\n"
        for i in range(1, n + 1)
    )


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeCollection:
    def __init__(self, existing=0, fail_on_batch=None):
        self.docs = existing
        self.fail_on_batch = fail_on_batch
        self.batches = 0
        self.calls = []

    async def count_documents(self, query):
        self.calls.append(("count_documents", query))
        return self.docs

    async def delete_many(self, query):
        self.calls.append(("delete_many", query))
        self.docs = 0

    async def insert_many(self, batch, ordered=True):
        self.batches += 1
        if self.fail_on_batch == self.batches:
            raise AutoReconnect(f"connection lost to {FAKE_URI}")
        self.calls.append(("insert_many", [dict(d) for d in batch], ordered))
        self.docs += len(batch)

    async def create_index(self, field, **kwargs):
        self.calls.append(("create_index", field, kwargs))

    @property
    def writes(self):
        return [c for c in self.calls if c[0] in ("delete_many", "insert_many", "create_index")]


class Env:
    def __init__(self, monkeypatch, tmp_path):
        self.monkeypatch = monkeypatch
        self.tmp_path = tmp_path
        self.collection = FakeCollection()
        self.connects = 0
        self.closes = 0
        self.accessed = []
        self.prompts = []
        self.answer = "yes"
        self.connect_error = None

        self.write_csv(HEADER + csv_rows(5))
        monkeypatch.setattr(hm, "BATCH_SIZE", 2)  # small batches for the tests only

        monkeypatch.setattr(hm.settings, "app_env", "development")
        monkeypatch.setattr(hm.settings, "database_name", "FixtureDB")
        monkeypatch.setattr(hm.settings, "mongodb_url", FAKE_URI)

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

        def fake_input(prompt=""):
            self.prompts.append(prompt)
            if isinstance(self.answer, BaseException):
                raise self.answer
            return self.answer

        monkeypatch.setattr(hm, "connect_db", connect_db)
        monkeypatch.setattr(hm, "close_db", close_db)
        monkeypatch.setattr(hm, "get_database", get_database)
        monkeypatch.setattr(hm, "input", fake_input, raising=False)

    def write_csv(self, text):
        path = self.tmp_path / "articles.csv"
        path.write_text(text, encoding="utf-8")
        self.monkeypatch.setattr(hm, "CSV_PATH", str(path))

    def existing(self, n):
        self.collection.docs = n

    def production(self):
        self.monkeypatch.setattr(hm.settings, "app_env", "production")


@pytest.fixture
def env(monkeypatch, tmp_path):
    return Env(monkeypatch, tmp_path)


def run(argv):
    return hm.main(argv)


def assert_no_credentials(text):
    for part in SECRET_PARTS:
        assert part not in text


BOTH = ["--apply", "--i-understand-this-replaces-catalog"]


# ---------------------------------------------------------------------------
# 1. Import safety and unchanged constants
# ---------------------------------------------------------------------------

def test_importing_has_no_side_effects(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("import_hm_catalog must not do this at import time")

    monkeypatch.setattr(database.connection, "connect_db", forbidden)
    monkeypatch.setattr(database.connection, "get_database", forbidden)
    monkeypatch.setattr(database.connection, "close_db", forbidden)
    monkeypatch.setattr("pandas.read_csv", forbidden)
    monkeypatch.setattr("builtins.input", forbidden)

    spec = importlib.util.spec_from_file_location("hm_import_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert callable(module.main)
    assert capsys.readouterr().out == ""


def test_import_constants_are_unchanged():
    assert hm.CSV_PATH == "../articles.csv"
    assert hm.COLLECTION_NAME == "catalog_products"
    assert hm.BATCH_SIZE == 5000
    assert hm.INDEXES == [
        ("article_id", True), ("name", False), ("category", False),
        ("department", False), ("colour", False),
    ]


# ---------------------------------------------------------------------------
# 2-3. Dry run
# ---------------------------------------------------------------------------

def test_default_invocation_is_a_dry_run(env, capsys):
    env.existing(7)

    assert run([]) == hm.EXIT_OK

    out = capsys.readouterr().out
    for expected in [
        "Target database   : FixtureDB",
        "Target collection : catalog_products",
        f"CSV source        : {hm.CSV_PATH}",
        "CSV rows          : 5",
        "Unique article IDs: 5",
        "Existing documents: 7",
        "Batch size        : 2",
        "removes ALL 7 documents",
        "insert_many in batches of 2 (ordered=False): 5 documents",
        "article_id (unique)",
        "DRY RUN: nothing was changed",
    ]:
        assert expected in out
    assert_no_credentials(out)


def test_dry_run_performs_no_writes_and_no_prompt(env):
    env.existing(7)

    assert run([]) == hm.EXIT_OK

    assert env.collection.writes == []
    assert env.collection.calls == [("count_documents", {})]
    assert env.prompts == []
    assert env.closes == env.connects == 1


# ---------------------------------------------------------------------------
# 4-6. Confirmation flags (non-production)
# ---------------------------------------------------------------------------

def test_apply_alone_refuses_to_replace_a_non_empty_collection(env, capsys):
    env.existing(7)

    assert run(["--apply"]) == hm.EXIT_REFUSED

    assert env.collection.writes == []
    assert env.prompts == []
    assert "--i-understand-this-replaces-catalog" in capsys.readouterr().out


def test_confirmation_alone_does_not_write(env, capsys):
    env.existing(7)

    assert run(["--i-understand-this-replaces-catalog"]) == hm.EXIT_REFUSED

    assert env.connects == 0
    assert env.collection.calls == []
    assert "has no effect without --apply" in capsys.readouterr().out


def test_both_flags_and_yes_run_the_unchanged_import(env, capsys):
    env.existing(7)

    assert run(BOTH) == hm.EXIT_OK

    names = [c[0] for c in env.collection.calls]
    assert names == (
        ["count_documents", "delete_many"] + ["insert_many"] * 3
        + ["create_index"] * 5 + ["count_documents"]
    )
    inserts = [c for c in env.collection.calls if c[0] == "insert_many"]
    assert [len(c[1]) for c in inserts] == [2, 2, 1]  # BATCH_SIZE batching
    assert all(c[2] is False for c in inserts)          # ordered=False
    assert inserts[0][1][0] == {
        "_id": "0100000001", "article_id": "0100000001", "name": "Item 1",
        "product_type": "Trousers", "category": "Garment Lower body", "department": "Denim",
        "section": "Womens Casual", "garment_group": "Trousers Denim", "colour": "Black",
        "description": "Description 1",
    }
    assert [c[1:] for c in env.collection.calls if c[0] == "create_index"] == [
        ("article_id", {"unique": True}), ("name", {}), ("category", {}),
        ("department", {}), ("colour", {}),
    ]
    assert env.accessed == ["catalog_products"]
    assert len(env.prompts) == 1
    out = capsys.readouterr().out
    assert "IMPORT COMPLETE" in out and "MongoDB documents: 5" in out
    assert_no_credentials(out)


# ---------------------------------------------------------------------------
# 7-9. Production
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("argv", [[], ["--apply"], BOTH], ids=["no-flags", "apply", "apply+confirm"])
@pytest.mark.parametrize("app_env", ["production", "PRODUCTION", " Production "])
def test_production_refuses_without_allow_production(env, monkeypatch, capsys, argv, app_env):
    env.existing(7)
    monkeypatch.setattr(hm.settings, "app_env", app_env)

    assert run(argv) == hm.EXIT_REFUSED

    assert env.connects == 0 and env.collection.calls == []
    assert "REFUSED: APP_ENV=production" in capsys.readouterr().out


def test_production_with_allow_still_requires_apply_for_writes(env):
    env.existing(7)
    env.production()

    assert run(["--allow-production"]) == hm.EXIT_OK  # read-only dry run
    assert env.collection.writes == []


def test_production_with_allow_still_requires_replace_confirmation(env, capsys):
    env.existing(7)
    env.production()

    assert run(["--allow-production", "--apply"]) == hm.EXIT_REFUSED
    assert env.collection.writes == [] and env.prompts == []

    assert run(["--allow-production", "--i-understand-this-replaces-catalog"]) == hm.EXIT_REFUSED
    assert env.collection.writes == []


def test_production_with_allow_still_requires_the_prompt(env):
    env.existing(7)
    env.production()
    env.answer = "no"

    assert run(["--allow-production"] + BOTH) == hm.EXIT_OK
    assert env.collection.writes == []


def test_production_write_path_with_every_confirmation(env):
    env.existing(7)
    env.production()

    assert run(["--allow-production"] + BOTH) == hm.EXIT_OK

    names = [c[0] for c in env.collection.writes]
    assert names == ["delete_many"] + ["insert_many"] * 3 + ["create_index"] * 5
    assert len(env.prompts) == 1


# ---------------------------------------------------------------------------
# 10. Empty collection
# ---------------------------------------------------------------------------

def test_empty_collection_dry_run_plans_no_delete(env, capsys):
    env.existing(0)

    assert run([]) == hm.EXIT_OK
    assert "no delete (catalog_products is empty)" in capsys.readouterr().out
    assert env.collection.writes == []


def test_empty_collection_imports_with_apply_alone_without_delete_or_prompt(env):
    env.existing(0)

    assert run(["--apply"]) == hm.EXIT_OK

    names = [c[0] for c in env.collection.writes]
    assert "delete_many" not in names
    assert names == ["insert_many"] * 3 + ["create_index"] * 5
    assert env.prompts == []


# ---------------------------------------------------------------------------
# 11-12. Missing or invalid CSV: nothing is touched
# ---------------------------------------------------------------------------

def test_missing_csv_fails_before_any_database_access(env, monkeypatch, capsys):
    monkeypatch.setattr(hm, "CSV_PATH", str(env.tmp_path / "does-not-exist.csv"))
    env.existing(7)

    assert run(BOTH) == hm.EXIT_ERROR

    assert env.connects == 0 and env.collection.calls == []
    assert "CSV not found" in capsys.readouterr().out


@pytest.mark.parametrize(
    "text,message",
    [
        (HEADER + csv_rows(3) + csv_rows(1), "Duplicate article_id"),
        ("article_id,prod_name\n0100000001,Item 1\n", "missing required columns"),
        ("", "could not be parsed"),
        (HEADER, "no rows"),
        (HEADER + ",Item,Trousers,Garment,Denim,Womens,Trousers Denim,Black,desc\n", "empty article_id"),
    ],
    ids=["duplicate-ids", "missing-columns", "empty-file", "header-only", "empty-article-id"],
)
def test_invalid_csv_fails_before_any_database_access(env, capsys, text, message):
    env.write_csv(text)
    env.existing(7)

    assert run(BOTH) == hm.EXIT_ERROR

    assert env.connects == 0 and env.collection.calls == []
    out = capsys.readouterr().out
    assert message in out and "Nothing was changed" in out


# ---------------------------------------------------------------------------
# 13. Interactive prompt (kept as an extra safeguard)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("answer", ["no", "", "y", "YES please"], ids=["no", "empty", "y", "yes-please"])
def test_prompt_anything_but_yes_cancels(env, capsys, answer):
    env.existing(7)
    env.answer = answer

    assert run(BOTH) == hm.EXIT_OK

    assert env.collection.writes == []
    assert "Import cancelled." in capsys.readouterr().out


def test_prompt_end_of_input_cancels(env):
    env.existing(7)
    env.answer = EOFError()

    assert run(BOTH) == hm.EXIT_OK
    assert env.collection.writes == []


@pytest.mark.parametrize("answer", ["yes", " YES ", "Yes"])
def test_prompt_yes_is_case_and_space_insensitive(env, answer):
    env.existing(7)
    env.answer = answer

    assert run(BOTH) == hm.EXIT_OK
    assert [c[0] for c in env.collection.writes][0] == "delete_many"


def test_prompt_mentions_the_existing_count(env):
    env.existing(7)

    run(BOTH)

    assert env.prompts == [
        "\ncatalog_products already contains 7 documents. Replace them? (yes/no): "
    ]


# ---------------------------------------------------------------------------
# 14. Credentials
# ---------------------------------------------------------------------------

def test_connection_error_does_not_print_credentials(env, capsys):
    env.connect_error = ServerSelectionTimeoutError(f"could not reach {FAKE_URI}")

    assert run([]) == hm.EXIT_ERROR

    out = capsys.readouterr().out
    assert "ServerSelectionTimeoutError" in out and "Nothing was changed" in out
    assert_no_credentials(out)
    assert env.collection.calls == []


# ---------------------------------------------------------------------------
# 15. Partial failure is reported (architecture unchanged)
# ---------------------------------------------------------------------------

def test_failure_mid_import_reports_a_partial_catalogue_without_leaking(env, capsys):
    env.existing(7)
    env.collection.fail_on_batch = 2

    assert run(BOTH) == hm.EXIT_ERROR

    names = [c[0] for c in env.collection.writes]
    assert names == ["delete_many", "insert_many"]  # stopped; no indexes
    out = capsys.readouterr().out
    assert "MongoDB operation failed (AutoReconnect)" in out
    assert "may now be PARTIAL (2/5 documents confirmed inserted)" in out
    assert_no_credentials(out)
    assert env.closes == 1
