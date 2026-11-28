"""WS-E3.7: the p-001 / p-005 image fix lives in the seed; the one-off patch is retired.

Static checks only: no MongoDB and no network.
"""

import subprocess
from pathlib import Path

import database.seed as seed_mod

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

# Same URLs as the frontend mock (src/lib/api/mock.ts, img() helper).
EXPECTED_IMAGES = {
    "p-001": "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?auto=format&fit=crop&w=800&q=80",
    "p-005": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=800&q=80",
}

# The URLs the retired update_product_images.py replaced (and the ones it set).
OLD_PHOTO_IDS = [
    "photo-1539533018447-63fcce2678e4",
    "photo-1625910513462-efd3f1751e7c",
]
PREMIUM_PHOTO_IDS = [
    "premium_photo-1718913936342-eaafff98834b",
    "premium_photo-1674719144570-0728faf14f96",
]


def _products_by_id():
    return {p["_id"]: p for p in seed_mod.PRODUCTS}


def test_p001_and_p005_use_the_frontend_mock_images():
    products = _products_by_id()
    for product_id, url in EXPECTED_IMAGES.items():
        assert products[product_id]["image"] == url


def test_frontend_mock_still_uses_the_same_photos():
    mock = (REPO_ROOT / "src" / "lib" / "api" / "mock.ts").read_text(encoding="utf-8")
    assert "https://images.unsplash.com/${id}?auto=format&fit=crop&w=800&q=80" in mock
    for url in EXPECTED_IMAGES.values():
        photo_id = url.split("/")[-1].split("?")[0]
        assert f'img("{photo_id}")' in mock


def test_old_and_premium_urls_are_absent_from_products():
    images = [p.get("image", "") for p in seed_mod.PRODUCTS]
    for photo_id in OLD_PHOTO_IDS + PREMIUM_PHOTO_IDS:
        assert not any(photo_id in image for image in images), photo_id


def test_other_products_are_unaffected():
    products = _products_by_id()
    assert len(products) == 12
    assert products["p-001"]["name"] == "Mercer Wool Overcoat"
    assert products["p-005"]["name"] == "Terry Polo Shirt"


def test_update_product_images_script_is_retired():
    assert not (BACKEND_DIR / "update_product_images.py").exists()


def test_no_tracked_file_references_the_retired_script():
    result = subprocess.run(
        ["git", "grep", "-n", "-I", "update_product_images", "--", "."],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    # git grep exits 1 when nothing matches.
    allowed = {
        "CATALOGIQ_AUDIT.md",  # historical review finding (H-12)
        "CATALOGIQ_AI_REVIEW.md",  # historical review finding (C-07)
        "backend/tests/test_seed_product_images.py",  # this test
    }
    hits = [
        line for line in result.stdout.splitlines()
        if line.split(":", 1)[0] not in allowed
    ]
    assert result.returncode in (0, 1), result.stderr
    assert hits == []
