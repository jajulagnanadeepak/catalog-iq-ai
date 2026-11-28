"""WS-E3.11: scripts/manual_intent_detection.py is retired.

It only printed IntentDetector results for 7 queries; tests/test_intent_detector.py
now asserts them. Static checks only: no MongoDB and no network.
"""

import subprocess
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

NAME = "manual_intent_detection"


def test_manual_intent_detection_script_is_retired():
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
    allowed = {"backend/tests/test_manual_intent_detection_retired.py"}  # this test
    hits = [
        line for line in result.stdout.splitlines()
        if line.split(":", 1)[0] not in allowed
    ]
    assert hits == []
