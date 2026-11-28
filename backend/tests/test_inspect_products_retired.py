"""WS-E3.8: scripts/inspect_broken_products.py is retired.

It only inspected the two images fixed in WS-E3.7; scripts/check_catalog.py
covers the same fields. Static checks only: no MongoDB and no network.
"""

import subprocess
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

NAME = "inspect_broken_products"


def test_inspect_broken_products_script_is_retired():
    assert not (BACKEND_DIR / "scripts" / f"{NAME}.py").exists()


def test_replacement_diagnostic_still_exists():
    assert (BACKEND_DIR / "scripts" / "check_catalog.py").exists()


def test_no_tracked_file_references_the_retired_script():
    result = subprocess.run(
        ["git", "grep", "-n", "-I", NAME, "--", "."],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    # git grep exits 1 when nothing matches.
    assert result.returncode in (0, 1), result.stderr
    allowed = {"backend/tests/test_inspect_products_retired.py"}  # this test
    hits = [
        line for line in result.stdout.splitlines()
        if line.split(":", 1)[0] not in allowed
    ]
    assert hits == []
