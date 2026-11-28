"""WS-E3.9: scripts/inspect_faiss_ids.py is retired.

It only inspected the legacy products.index / product_ids.pkl pair, whose
builder was retired in WS-E3.4 and which search.py never loads. Static checks
only: no MongoDB, no network and no index loading.
"""

import subprocess
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

NAME = "inspect_faiss_ids"


def test_inspect_faiss_ids_script_is_retired():
    assert not (BACKEND_DIR / "scripts" / f"{NAME}.py").exists()


def test_no_tracked_file_references_the_retired_script():
    result = subprocess.run(
        ["git", "grep", "-n", "-I", NAME, "--", "."],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    # git grep exits 1 when nothing matches.
    assert result.returncode in (0, 1), result.stderr
    allowed = {"backend/tests/test_inspect_faiss_ids_retired.py"}  # this test
    hits = [
        line for line in result.stdout.splitlines()
        if line.split(":", 1)[0] not in allowed
    ]
    assert hits == []


def test_readme_diagnostic_table_does_not_list_it():
    readme = (BACKEND_DIR / "README.md").read_text(encoding="utf-8")
    assert "#### Diagnostic scripts (`scripts/`)" in readme
    table_rows = [line for line in readme.splitlines() if line.startswith("| `")]
    assert table_rows, "diagnostic table not found"
    assert not any(f"`{NAME}`" in row for row in table_rows)
