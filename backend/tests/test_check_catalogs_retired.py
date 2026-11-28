"""WS-E3.14: scripts/check_catalogs.py is retired.

It compared ``products`` with the legacy ``Products`` collection, whose only
writer (the root seed.py) was retired in WS-E3.13 and which no application code
reads. check_catalog.py and check_hm_catalog.py cover the active collections.
Static checks only: no MongoDB and no network.
"""

import subprocess
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
SCRIPTS_DIR = BACKEND_DIR / "scripts"

NAME = "check_catalogs"
THIS_TEST = "backend/tests/test_check_catalogs_retired.py"


def _git_grep(*args):
    result = subprocess.run(
        ["git", "grep", "-n", "-I", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    # git grep exits 1 when nothing matches.
    assert result.returncode in (0, 1), result.stderr
    return [
        line for line in result.stdout.splitlines()
        if line.split(":", 1)[0] != THIS_TEST
    ]


def test_check_catalogs_script_is_retired():
    assert not (SCRIPTS_DIR / f"{NAME}.py").exists()


def test_check_catalog_script_still_exists():
    assert (SCRIPTS_DIR / "check_catalog.py").exists()


def test_check_hm_catalog_script_still_exists():
    assert (SCRIPTS_DIR / "check_hm_catalog.py").exists()


def test_no_tracked_file_references_the_retired_script():
    # Literal "check_catalogs": it does not match the active "check_catalog".
    assert _git_grep("-F", NAME, "--", ".") == []


def test_no_python_code_reads_the_legacy_products_collection():
    # Legacy collection reference this guard looks for: db["Products"] (also
    # get_database()["Products"]). The Swagger tag tags=["Products"] is not a
    # collection and must not match.
    pattern = r"(\bdb|get_database\(\))\s*\[\s*[\"']Products[\"']\s*\]"
    assert _git_grep("-E", pattern, "--", "*.py") == []
