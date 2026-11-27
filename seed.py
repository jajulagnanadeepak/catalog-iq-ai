"""Seed the legacy ``CatalogIQ.Products`` collection from ``articles.csv``.

DESTRUCTIVE: a real run deletes EVERY document in ``CatalogIQ.Products``,
inserts one document per CSV row and creates the indexes below.

Safety (Phase 1 WS-E3.1):
* importing this module does nothing (no DB connection, no reads, no writes);
* running it without flags is a dry run: it reports the target, the CSV row
  count, the existing document count (read-only) and the planned operations;
* writes need BOTH ``--apply`` and ``--i-understand-this-deletes``;
* it always refuses to run when ``APP_ENV=production``, whatever the flags;
* the MongoDB URI is never printed.

Usage (from the repository root, with ``MONGO_URI`` in ``.env``):
    python seed.py                                        # dry run
    python seed.py --apply --i-understand-this-deletes    # deletes + re-imports
"""

import argparse
import os
import sys

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

DATABASE_NAME = "CatalogIQ"
COLLECTION_NAME = "Products"
CSV_PATH = "articles.csv"

# (field, unique) in creation order
INDEXES = [
    ("product_id", True),
    ("name", False),
    ("category", False),
    ("department", False),
    ("colour", False),
]

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_REFUSED = 2


def build_records(df):
    """Convert CSV rows into MongoDB documents (unchanged mapping)."""
    records = []

    for _, row in df.iterrows():

        product = {

            "product_id": str(row["article_id"]),

            "name": row["prod_name"],

            "product_type": row["product_type_name"],

            "category": row["product_group_name"],

            "department": row["department_name"],

            "section": row["section_name"],

            "garment_group": row["garment_group_name"],

            "colour": row["colour_group_name"],

            "description": row["detail_desc"] if pd.notna(row["detail_desc"]) else ""

        }

        records.append(product)

    return records


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            f"Seed {DATABASE_NAME}.{COLLECTION_NAME} from {CSV_PATH}. "
            "Dry run unless both --apply and --i-understand-this-deletes are given."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="perform the writes (requires --i-understand-this-deletes)",
    )
    parser.add_argument(
        "--i-understand-this-deletes",
        dest="confirm_delete",
        action="store_true",
        help=f"confirm that every document in {COLLECTION_NAME} will be deleted",
    )
    return parser.parse_args(argv)


def _is_production():
    return os.getenv("APP_ENV", "").strip().lower() == "production"


def _print_plan(csv_rows, existing):
    existing_text = f"{existing:,}" if existing is not None else "unknown (MONGO_URI not set)"
    index_text = ", ".join(f"{field}{' (unique)' if unique else ''}" for field, unique in INDEXES)

    print("--------------------------------------")
    print(f"Target database   : {DATABASE_NAME}")
    print(f"Target collection : {COLLECTION_NAME}")
    print(f"CSV file          : {CSV_PATH}")
    print(f"CSV rows          : {csv_rows:,}")
    print(f"Existing documents: {existing_text}")
    print("Planned operations:")
    print(f"  1. delete_many({{}}) on {COLLECTION_NAME}: removes ALL existing documents")
    print(f"  2. insert_many: {csv_rows:,} documents")
    print(f"  3. create indexes: {index_text}")
    print("--------------------------------------")


def main(argv=None, client_factory=None):
    args = parse_args(argv)

    # --------------------------------------------------
    # Load environment variables
    # --------------------------------------------------
    load_dotenv()

    # Production is refused first; no flag combination bypasses it.
    if _is_production():
        print("REFUSED: APP_ENV=production. This script never runs in production.")
        return EXIT_REFUSED

    # Writes need both flags; one without the other is refused.
    if args.apply != args.confirm_delete:
        missing = "--i-understand-this-deletes" if args.apply else "--apply"
        print(
            f"REFUSED: writes need both --apply and --i-understand-this-deletes "
            f"(missing {missing}). Nothing was changed."
        )
        return EXIT_REFUSED

    apply = args.apply and args.confirm_delete

    mongo_uri = os.getenv("MONGO_URI")

    if apply and not mongo_uri:
        print("❌ MONGO_URI not found in .env file")
        return EXIT_ERROR

    # --------------------------------------------------
    # Read CSV
    # --------------------------------------------------
    print(f"📄 Reading {CSV_PATH}...")

    df = pd.read_csv(CSV_PATH)

    print(f"📦 Found {len(df)} products.")

    records = build_records(df)

    if not mongo_uri:
        # Dry run without a URI: report the plan without touching MongoDB.
        _print_plan(len(records), existing=None)
        print("DRY RUN: nothing was changed. Writes need --apply --i-understand-this-deletes.")
        return EXIT_OK

    # --------------------------------------------------
    # Connect to MongoDB Atlas (URI is never printed)
    # --------------------------------------------------
    print("🔄 Connecting to MongoDB Atlas...")

    try:
        client = (client_factory or MongoClient)(mongo_uri)

        # Test connection
        client.admin.command("ping")

        print("✅ Connected Successfully!")

        # --------------------------------------------------
        # Database & Collection
        # --------------------------------------------------
        db = client[DATABASE_NAME]
        products = db[COLLECTION_NAME]

        existing = products.count_documents({})  # read-only

        _print_plan(len(records), existing)

        if not apply:
            print("DRY RUN: nothing was changed. Writes need --apply --i-understand-this-deletes.")
            return EXIT_OK

        # --------------------------------------------------
        # Clear old data
        # --------------------------------------------------
        products.delete_many({})
        print("🗑 Existing products removed.")

        # --------------------------------------------------
        # Insert Products
        # --------------------------------------------------
        print("🚀 Uploading products to MongoDB...")

        products.insert_many(records)

        # --------------------------------------------------
        # Create useful indexes
        # --------------------------------------------------
        for field, unique in INDEXES:
            if unique:
                products.create_index(field, unique=True)
            else:
                products.create_index(field)

        print("✅ Indexes created.")

    except PyMongoError as exc:
        # Report only the error type: messages can contain connection details.
        print(f"❌ MongoDB operation failed ({type(exc).__name__}). Check MONGO_URI and network access.")
        return EXIT_ERROR

    print("--------------------------------------")
    print(f"🎉 Successfully Imported {len(records)} Products")
    print("--------------------------------------")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
