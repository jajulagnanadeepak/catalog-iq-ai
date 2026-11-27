"""Import the H&M catalogue (``articles.csv``) into ``catalog_products``.

DESTRUCTIVE: if ``catalog_products`` already holds documents, a real run
deletes ALL of them and re-imports the CSV (``_id`` = ``article_id``, so the
FAISS id mapping stays valid).

Safety (Phase 1 WS-E3.2):
* importing this module does nothing (no DB connection, no reads, no writes);
* the CSV is fully read and validated before any database access, so a
  missing or invalid CSV never deletes anything;
* without ``--apply`` it is a dry run: it reports the plan and changes nothing;
* replacing a non-empty collection also needs
  ``--i-understand-this-replaces-catalog`` and then the existing interactive
  "yes" prompt;
* ``APP_ENV=production`` is refused unless ``--allow-production`` is given,
  and production writes still need every flag and the prompt above;
* database errors are reported by type only (no URI or credentials).

Usage (from ``backend/``):
    python -m database.import_hm_catalog                      # dry run
    python -m database.import_hm_catalog --apply              # empty collection only
    python -m database.import_hm_catalog --apply --i-understand-this-replaces-catalog
"""

import argparse
import asyncio
import sys

import pandas as pd

from config import settings
from database.connection import connect_db, close_db, get_database


CSV_PATH = "../articles.csv"
COLLECTION_NAME = "catalog_products"
BATCH_SIZE = 5000

REQUIRED_COLUMNS = (
    "article_id",
    "prod_name",
    "product_type_name",
    "product_group_name",
    "department_name",
    "section_name",
    "garment_group_name",
    "colour_group_name",
    "detail_desc",
)

# (field, unique) in creation order
INDEXES = [
    ("article_id", True),
    ("name", False),
    ("category", False),
    ("department", False),
    ("colour", False),
]

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_REFUSED = 2


class CatalogInputError(Exception):
    """The CSV cannot be imported safely."""


def build_records(df):
    """CSV rows -> catalog_products documents (unchanged mapping)."""
    records = []

    for _, row in df.iterrows():
        records.append(
            {
                "_id": row["article_id"],
                "article_id": row["article_id"],
                "name": row["prod_name"],
                "product_type": row["product_type_name"],
                "category": row["product_group_name"],
                "department": row["department_name"],
                "section": row["section_name"],
                "garment_group": row["garment_group_name"],
                "colour": row["colour_group_name"],
                "description": row["detail_desc"],
            }
        )

    return records


def load_and_validate(csv_path):
    """Read and validate the CSV. Raises CatalogInputError; never touches the DB."""
    try:
        df = pd.read_csv(
            csv_path,
            dtype={"article_id": str},
            keep_default_na=False,
        )
    except FileNotFoundError as exc:
        raise CatalogInputError(f"CSV not found: {csv_path}") from exc
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise CatalogInputError(f"CSV could not be parsed ({type(exc).__name__}): {csv_path}") from exc

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise CatalogInputError(f"CSV is missing required columns: {', '.join(missing)}")

    if len(df) == 0:
        raise CatalogInputError("CSV has no rows; refusing to replace the catalogue with nothing.")

    if (df["article_id"].str.strip() == "").any():
        raise CatalogInputError("CSV contains empty article_id values.")

    print(f"CSV rows: {len(df):,}")
    print(f"Unique article IDs: {df['article_id'].nunique():,}")

    if len(df) != df["article_id"].nunique():
        raise CatalogInputError("Duplicate article_id values detected.")

    return df, build_records(df)


def _is_production():
    return str(settings.app_env).strip().lower() == "production"


def _print_plan(csv_path, csv_rows, unique_ids, existing):
    index_text = ", ".join(f"{field}{' (unique)' if unique else ''}" for field, unique in INDEXES)

    print("-" * 60)
    print(f"Target database   : {settings.database_name}")
    print(f"Target collection : {COLLECTION_NAME}")
    print(f"CSV source        : {csv_path}")
    print(f"CSV rows          : {csv_rows:,}")
    print(f"Unique article IDs: {unique_ids:,}")
    print(f"Existing documents: {existing:,}")
    print(f"Batch size        : {BATCH_SIZE:,}")
    print("Planned operations:")
    if existing > 0:
        print(f"  1. delete_many({{}}) on {COLLECTION_NAME}: removes ALL {existing:,} documents")
    else:
        print(f"  1. no delete ({COLLECTION_NAME} is empty)")
    print(f"  2. insert_many in batches of {BATCH_SIZE:,} (ordered=False): {csv_rows:,} documents")
    print(f"  3. create indexes: {index_text}")
    print("-" * 60)


async def import_catalog(apply=False, confirm_replace=False, allow_production=False):
    print("=" * 60)
    print("CatalogIQ H&M Catalog Import")
    print("=" * 60)

    # Production is refused unless explicitly allowed; it never skips the
    # other confirmations.
    if _is_production() and not allow_production:
        print("REFUSED: APP_ENV=production. Re-run with --allow-production to override.")
        return EXIT_REFUSED

    if confirm_replace and not apply:
        print(
            "REFUSED: --i-understand-this-replaces-catalog has no effect without --apply. "
            "Nothing was changed."
        )
        return EXIT_REFUSED

    # Validate the input fully before any database access.
    csv_path = CSV_PATH
    print(f"\nReading {csv_path}...")

    try:
        df, records = load_and_validate(csv_path)
    except CatalogInputError as exc:
        print(f"ERROR: {exc} Nothing was changed.")
        return EXIT_ERROR

    print(f"Prepared {len(records):,} documents.")

    try:
        await connect_db()
    except Exception as exc:
        # Report only the error type: messages can contain connection details.
        print(f"ERROR: could not connect to MongoDB ({type(exc).__name__}). Nothing was changed.")
        return EXIT_ERROR

    inserted = 0

    try:
        db = get_database()
        collection = db[COLLECTION_NAME]

        print(f"\nMongoDB collection: {COLLECTION_NAME}")

        existing = await collection.count_documents({})
        print(f"Existing documents: {existing:,}")

        _print_plan(csv_path, len(records), df["article_id"].nunique(), existing)

        if not apply:
            print("DRY RUN: nothing was changed. Writes need --apply.")
            return EXIT_OK

        if existing > 0:
            if not confirm_replace:
                print(
                    f"REFUSED: {COLLECTION_NAME} already contains {existing:,} documents. "
                    "Replacing it needs --i-understand-this-replaces-catalog. Nothing was changed."
                )
                return EXIT_REFUSED

            try:
                answer = input(
                    f"\n{COLLECTION_NAME} already contains {existing:,} documents. "
                    "Replace them? (yes/no): "
                ).strip().lower()
            except EOFError:
                answer = ""

            if answer != "yes":
                print("Import cancelled.")
                return EXIT_OK

            await collection.delete_many({})
            print("Existing catalog removed.")

        for start in range(0, len(records), BATCH_SIZE):
            batch = records[start : start + BATCH_SIZE]

            await collection.insert_many(
                batch,
                ordered=False,
            )
            inserted = min(start + BATCH_SIZE, len(records))

            print(
                f"Inserted {inserted:,}"
                f"/{len(records):,}"
            )

        print("\nCreating indexes...")

        for field, unique in INDEXES:
            if unique:
                await collection.create_index(field, unique=True)
            else:
                await collection.create_index(field)

        final_count = await collection.count_documents({})

        print("\n" + "=" * 60)
        print("IMPORT COMPLETE")
        print("=" * 60)
        print(f"MongoDB documents: {final_count:,}")
        return EXIT_OK

    except Exception as exc:
        # Report only the error type: messages can contain connection details.
        print(f"ERROR: MongoDB operation failed ({type(exc).__name__}).")
        if apply and inserted < len(records):
            print(
                f"WARNING: {COLLECTION_NAME} may now be PARTIAL "
                f"({inserted:,}/{len(records):,} documents confirmed inserted). "
                "Re-run the import with the same flags to replace it again."
            )
        return EXIT_ERROR

    finally:
        await close_db()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            f"Import articles.csv into {COLLECTION_NAME}. "
            "Dry run unless --apply is given."
        )
    )
    parser.add_argument("--apply", action="store_true", help="perform the import")
    parser.add_argument(
        "--i-understand-this-replaces-catalog",
        dest="confirm_replace",
        action="store_true",
        help=f"confirm deleting every existing document in {COLLECTION_NAME}",
    )
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="allow running when APP_ENV=production (all other confirmations still apply)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    return asyncio.run(
        import_catalog(
            apply=args.apply,
            confirm_replace=args.confirm_replace,
            allow_production=args.allow_production,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
