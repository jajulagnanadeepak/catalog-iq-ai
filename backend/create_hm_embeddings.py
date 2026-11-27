"""Build the H&M semantic-search artefacts from ``catalog_products``.

Writes ``hm_products.index`` (FAISS) and ``hm_product_ids.pkl`` (row -> article_id)
next to this file, which is where ``search.py`` loads them from.

Safety (Phase 1 WS-E3.3):
* importing this module does nothing (no DB connection, no model, no writes);
* without ``--apply`` it is a dry run: a read-only catalogue count plus a
  read-only inspection of the existing artefacts; no model is loaded;
* if either artefact already exists, ``--apply`` also needs
  ``--i-understand-this-overwrites-index``;
* ``APP_ENV=production`` is refused unless ``--allow-production`` is given
  (all other flags still apply);
* the catalogue is validated before the model is loaded;
* both artefacts are written to ``*.tmp`` files, validated, and only then
  promoted; the previous pair is kept as ``*.bak``. A failed promotion is
  rolled back to the previous pair and the result is verified;
* database errors are reported by type only (no URI or credentials).

Usage (from ``backend/``):
    python create_hm_embeddings.py                                              # dry run
    python create_hm_embeddings.py --apply                                      # first build
    python create_hm_embeddings.py --apply --i-understand-this-overwrites-index # rebuild
"""

import argparse
import asyncio
import os
import pickle
import sys
from datetime import datetime
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from config import settings
from database.connection import connect_db, close_db, get_database


MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION_NAME = "catalog_products"

# Same location search.py loads from (BASE_DIR), whatever the working directory.
ARTIFACT_DIR = Path(__file__).resolve().parent
INDEX_PATH = ARTIFACT_DIR / "hm_products.index"
IDS_PATH = ARTIFACT_DIR / "hm_product_ids.pkl"

ENCODE_BATCH_SIZE = 64  # used verbatim in model.encode(...) below
TMP_SUFFIX = ".tmp"
BAK_SUFFIX = ".bak"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_REFUSED = 2
EXIT_ROLLBACK_FAILED = 3


class EmbeddingsError(Exception):
    """A safety or validation check failed (message is safe to print)."""


class RollbackFailed(Exception):
    """Promotion failed and the previous artefacts could not be restored."""


# ---------------------------------------------------------------------------
# Small wrappers (one place per filesystem/FAISS operation; tests patch these)
# ---------------------------------------------------------------------------

def _write_index(index, path):
    faiss.write_index(index, str(path))


def _write_ids(product_ids, path):
    with open(path, "wb") as f:
        pickle.dump(product_ids, f)


def _replace(src, dst):
    os.replace(src, dst)


def _with_suffix(path, suffix):
    return Path(path).with_name(Path(path).name + suffix)


def _is_production():
    return str(settings.app_env).strip().lower() == "production"


# ---------------------------------------------------------------------------
# Read-only inspection
# ---------------------------------------------------------------------------

def _file_info(path):
    path = Path(path)
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    return {
        "exists": True,
        "size": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
    }


def inspect_artifacts(index_path, ids_path):
    """Read-only status of an index/ID pair (loads both files if present)."""
    info = {"index": _file_info(index_path), "ids": _file_info(ids_path)}

    if info["index"]["exists"]:
        try:
            index = faiss.read_index(str(index_path))
            info["index"].update(ntotal=index.ntotal, dimension=index.d)
        except Exception as exc:  # noqa: BLE001 - reported, never raised
            info["index"]["error"] = type(exc).__name__

    if info["ids"]["exists"]:
        try:
            with open(ids_path, "rb") as f:
                info["ids"]["count"] = len(pickle.load(f))
        except Exception as exc:  # noqa: BLE001
            info["ids"]["error"] = type(exc).__name__

    if not info["index"]["exists"] and not info["ids"]["exists"]:
        info["pair"] = "none"
    elif "ntotal" in info["index"] and "count" in info["ids"]:
        info["pair"] = (
            "consistent" if info["index"]["ntotal"] == info["ids"]["count"] else "MISMATCH"
        )
    else:
        info["pair"] = "INCOMPLETE or UNREADABLE"
    return info


def _print_artifact(label, path, data):
    if not data["exists"]:
        print(f"  {label}: {path} (missing)")
        return
    extra = []
    if "ntotal" in data:
        extra.append(f"ntotal={data['ntotal']:,}, dimension={data['dimension']}")
    if "count" in data:
        extra.append(f"ids={data['count']:,}")
    if "error" in data:
        extra.append(f"UNREADABLE ({data['error']})")
    print(f"  {label}: {path} ({data['size']:,} bytes, modified {data['mtime']}; {', '.join(extra)})")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_products(products, expected_count):
    if len(products) != expected_count:
        raise EmbeddingsError(
            f"Loaded {len(products):,} products but counted {expected_count:,}; "
            "the catalogue changed while reading."
        )
    seen = set()
    for product in products:
        article_id = product.get("article_id")
        if article_id is None or str(article_id).strip() == "":
            raise EmbeddingsError(f"Product {product.get('_id')!r} has no article_id.")
        if article_id in seen:
            raise EmbeddingsError(f"Duplicate article_id {article_id!r}.")
        seen.add(article_id)


def validate_temp_artifacts(tmp_index, tmp_ids, expected_ids, expected_dimension):
    index = faiss.read_index(str(tmp_index))
    if index.ntotal != len(expected_ids):
        raise EmbeddingsError(
            f"Temporary index has {index.ntotal:,} vectors, expected {len(expected_ids):,}."
        )
    if index.d != expected_dimension:
        raise EmbeddingsError(
            f"Temporary index dimension is {index.d}, expected {expected_dimension}."
        )
    with open(tmp_ids, "rb") as f:
        loaded = pickle.load(f)
    if loaded != expected_ids:
        raise EmbeddingsError("Temporary ID map does not match the expected IDs and order.")


# ---------------------------------------------------------------------------
# Promotion with backup and rollback
# ---------------------------------------------------------------------------

def promote(tmp_index, tmp_ids, index_path, ids_path):
    """Move the validated pair into place, keeping the previous pair as *.bak.

    On failure, restore the previous pair (or remove a half-promoted first
    build) and verify the result. Raises the original error, or RollbackFailed.
    """
    pairs = [(Path(index_path), Path(tmp_index)), (Path(ids_path), Path(tmp_ids))]
    before = inspect_artifacts(index_path, ids_path)
    backed_up, promoted = [], []

    try:
        # The .bak pair must describe one previous state: drop a stale backup of
        # an artefact that is missing now, then back up what exists.
        for live, _ in pairs:
            bak = _with_suffix(live, BAK_SUFFIX)
            if not live.exists() and bak.exists():
                bak.unlink()
        for live, _ in pairs:
            if live.exists():
                _replace(live, _with_suffix(live, BAK_SUFFIX))
                backed_up.append(live)
        for live, tmp in pairs:
            _replace(tmp, live)
            promoted.append(live)
    except Exception as exc:
        try:
            for live in promoted:
                if live not in backed_up and live.exists():
                    live.unlink()  # first build: no previous file to restore
            for live in backed_up:
                _replace(_with_suffix(live, BAK_SUFFIX), live)
            after = inspect_artifacts(index_path, ids_path)
        except Exception as rb_exc:
            raise RollbackFailed(
                f"promotion failed ({type(exc).__name__}) and restoring the previous "
                f"artefacts failed ({type(rb_exc).__name__})"
            ) from rb_exc
        if after != before:
            raise RollbackFailed(
                f"promotion failed ({type(exc).__name__}); the restored artefacts differ "
                f"from the previous ones (pair '{after['pair']}', was '{before['pair']}')"
            ) from exc
        raise


def _cleanup(*paths):
    for path in paths:
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

async def create_embeddings(apply=False, confirm_overwrite=False, allow_production=False):
    print("=" * 60)
    print("CatalogIQ H&M Semantic Search Index")
    print("=" * 60)

    if _is_production() and not allow_production:
        print("REFUSED: APP_ENV=production. Re-run with --allow-production to override.")
        return EXIT_REFUSED

    if confirm_overwrite and not apply:
        print(
            "REFUSED: --i-understand-this-overwrites-index has no effect without --apply. "
            "Nothing was changed."
        )
        return EXIT_REFUSED

    index_path, ids_path = Path(INDEX_PATH), Path(IDS_PATH)
    tmp_index, tmp_ids = _with_suffix(index_path, TMP_SUFFIX), _with_suffix(ids_path, TMP_SUFFIX)
    existing = [p for p in (index_path, ids_path) if p.exists()]

    if apply and existing and not confirm_overwrite:
        print(
            "REFUSED: existing artefacts would be overwritten: "
            + ", ".join(p.name for p in existing)
            + ". Re-run with --i-understand-this-overwrites-index. Nothing was changed."
        )
        return EXIT_REFUSED

    stage = "database connection"
    try:
        await connect_db()
    except Exception as exc:
        # Report only the error type: messages can contain connection details.
        print(f"ERROR: could not connect to MongoDB ({type(exc).__name__}). Nothing was changed.")
        return EXIT_ERROR

    temps_written = False
    try:
        stage = "catalogue read"
        db = get_database()
        collection = db[COLLECTION_NAME]

        count = await collection.count_documents({})

        print(f"\nCatalog documents: {count:,}")

        if count == 0:
            raise EmbeddingsError("catalog_products is empty. Run the H&M import first.")

        if not apply:
            artifacts = inspect_artifacts(index_path, ids_path)
            print("-" * 60)
            print(f"Target directory  : {index_path.parent}")
            print(f"Model             : {MODEL_NAME}")
            print(f"Encode batch size : {ENCODE_BATCH_SIZE}")
            print(f"Catalogue count   : {count:,}")
            print("Existing artefacts:")
            _print_artifact("index", index_path, artifacts["index"])
            _print_artifact("ids  ", ids_path, artifacts["ids"])
            print(f"  pair: {artifacts['pair']}")
            print("Planned operations (with --apply):")
            print(f"  1. load {count:,} products, validate article_id values")
            print(f"  2. load model {MODEL_NAME}, encode in batches of {ENCODE_BATCH_SIZE}")
            print(f"  3. write {tmp_index.name} and {tmp_ids.name}, validate both")
            if existing:
                print(f"  4. back up the current pair to *{BAK_SUFFIX}, then replace it "
                      "(needs --i-understand-this-overwrites-index)")
            else:
                print("  4. move the new pair into place (no existing artefacts)")
            print("-" * 60)
            print("DRY RUN: nothing was changed. Writes need --apply.")
            return EXIT_OK

        print("\nLoading catalog...")

        products = await collection.find(
            {},
            {
                "_id": 1,
                "article_id": 1,
                "name": 1,
                "product_type": 1,
                "category": 1,
                "department": 1,
                "section": 1,
                "garment_group": 1,
                "colour": 1,
                "description": 1,
            },
        ).sort("_id", 1).to_list(length=None)

        print(f"Loaded: {len(products):,}")

        stage = "catalogue validation"
        validate_products(products, count)

        texts = []
        product_ids = []

        print("\nPreparing embedding text...")

        for product in products:

            text = " ".join(
                [
                    str(product.get("name", "")),
                    str(product.get("product_type", "")),
                    str(product.get("category", "")),
                    str(product.get("department", "")),
                    str(product.get("section", "")),
                    str(product.get("garment_group", "")),
                    str(product.get("colour", "")),
                    str(product.get("description", "")),
                ]
            )

            texts.append(text)
            product_ids.append(product["article_id"])

        print(f"Prepared: {len(texts):,}")

        stage = "model load"
        print("\nLoading Sentence Transformer...")
        model = SentenceTransformer(MODEL_NAME)
        print("✅ Model Loaded")

        stage = "embedding generation"
        print("\nGenerating embeddings...")

        embeddings = model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=True,
            batch_size=64,
        )

        embeddings = embeddings.astype(np.float32)

        print(f"Embedding shape: {embeddings.shape}")

        dimension = embeddings.shape[1]

        print("\nCreating FAISS index...")

        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)

        print(f"FAISS vectors: {index.ntotal:,}")
        print(f"FAISS dimension: {index.d}")

        stage = "temporary artefact write"
        print("\nSaving index...")

        temps_written = True
        _write_index(index, tmp_index)
        _write_ids(product_ids, tmp_ids)

        stage = "temporary artefact validation"
        validate_temp_artifacts(tmp_index, tmp_ids, product_ids, dimension)

        stage = "promotion"
        promote(tmp_index, tmp_ids, index_path, ids_path)
        stage = "report"

        print(f"✅ Saved: {index_path}")
        print(f"✅ Saved: {ids_path}")
        if existing:
            print(f"Previous pair kept as *{BAK_SUFFIX} next to the artefacts.")

        print("\nVerifying mapping...")

        print("First 5 mappings:")

        for i in range(min(5, len(product_ids))):
            print(
                f"FAISS {i} -> article_id {product_ids[i]}"
            )

        print("\n" + "=" * 60)
        print("H&M FAISS INDEX COMPLETE")
        print("=" * 60)
        return EXIT_OK

    except RollbackFailed as exc:
        temps_written = False  # keep the temporary files for manual recovery
        print(f"ROLLBACK FAILED: {exc}.")
        print(
            f"The live artefacts may be inconsistent. Recover manually from the "
            f"*{BAK_SUFFIX} and *{TMP_SUFFIX} files in {index_path.parent}."
        )
        return EXIT_ROLLBACK_FAILED

    except EmbeddingsError as exc:
        print(f"ERROR during {stage}: {exc} Live artefacts were not changed.")
        return EXIT_ERROR

    except Exception as exc:
        # Report only the error type: messages can contain connection details.
        if stage == "promotion":
            print(f"ERROR during promotion ({type(exc).__name__}). "
                  "The previous artefacts were restored and verified.")
        elif stage == "report":
            print(f"ERROR while reporting ({type(exc).__name__}). "
                  "The new artefacts are already in place and were validated.")
        else:
            print(f"ERROR during {stage} ({type(exc).__name__}). Live artefacts were not changed.")
        return EXIT_ERROR

    finally:
        if temps_written:
            _cleanup(tmp_index, tmp_ids)
        await close_db()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build the H&M FAISS index and ID map. Dry run unless --apply is given."
    )
    parser.add_argument("--apply", action="store_true", help="generate and write the artefacts")
    parser.add_argument(
        "--i-understand-this-overwrites-index",
        dest="confirm_overwrite",
        action="store_true",
        help="confirm replacing existing artefacts (the previous pair is kept as *.bak)",
    )
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="allow running when APP_ENV=production (all other flags still apply)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    return asyncio.run(
        create_embeddings(
            apply=args.apply,
            confirm_overwrite=args.confirm_overwrite,
            allow_production=args.allow_production,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
