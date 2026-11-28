"""WS-E3.13: the repository-root seed.py (legacy ``Products`` seeder) is retired.

It deleted and re-imported ``CatalogIQ.Products``, which nothing in the app reads.
The live catalogue comes from database/import_hm_catalog.py (``catalog_products``)
and the demo products from database/seed.py (``products``); both still need
articles.csv / their own data and are kept. Static checks only: no MongoDB,
no network, and no seeder or importer is run.
"""

import subprocess
from pathlib import Path

import database.import_hm_catalog as hm

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
ARTICLES_CSV = REPO_ROOT / "articles.csv"

# Historical review / planning documents that describe the retired seeder.
HISTORICAL_DOCS = {
    "CATALOGIQ_AUDIT.md",
    "CATALOGIQ_SECURITY_REVIEW.md",
    "PHASE1_PLAN.md",
}


def test_root_seed_is_retired():
    assert not (REPO_ROOT / "seed.py").exists()


def test_demo_products_seed_still_exists():
    assert (BACKEND_DIR / "database" / "seed.py").exists()


def test_articles_csv_still_exists():
    assert ARTICLES_CSV.is_file()


def test_import_hm_catalog_csv_path_resolves_to_articles_csv():
    # import_hm_catalog is run from backend/, so its path is relative to it.
    resolved = (BACKEND_DIR / hm.CSV_PATH).resolve()
    assert resolved == ARTICLES_CSV.resolve()
    with resolved.open(encoding="utf-8") as fh:
        header = fh.readline().strip().split(",")
    assert set(hm.REQUIRED_COLUMNS) <= set(header)


def test_root_seeder_flags_and_env_var_are_not_referenced():
    # --i-understand-this-deletes and MONGO_URI belonged only to the root seeder.
    result = subprocess.run(
        ["git", "grep", "-n", "-I", "-E", "i-understand-this-deletes|MONGO_URI", "--", "."],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    # git grep exits 1 when nothing matches.
    assert result.returncode in (0, 1), result.stderr
    allowed = HISTORICAL_DOCS | {"backend/tests/test_root_seed_retired.py"}  # + this test
    hits = [
        line for line in result.stdout.splitlines()
        if line.split(":", 1)[0] not in allowed
    ]
    assert hits == []
