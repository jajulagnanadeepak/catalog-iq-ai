import asyncio
import pandas as pd

from database.connection import connect_db, close_db, get_database


CSV_PATH = "../articles.csv"
COLLECTION_NAME = "catalog_products"


async def import_catalog():
    print("=" * 60)
    print("CatalogIQ H&M Catalog Import")
    print("=" * 60)

    print("\nReading articles.csv...")

    df = pd.read_csv(
        CSV_PATH,
        dtype={"article_id": str},
        keep_default_na=False,
    )

    print(f"CSV rows: {len(df):,}")
    print(f"Unique article IDs: {df['article_id'].nunique():,}")

    if len(df) != df["article_id"].nunique():
        raise ValueError("Duplicate article_id values detected.")

    await connect_db()

    try:
        db = get_database()
        collection = db[COLLECTION_NAME]

        print(f"\nMongoDB collection: {COLLECTION_NAME}")

        existing = await collection.count_documents({})
        print(f"Existing documents: {existing:,}")

        if existing > 0:
            answer = input(
                f"\n{COLLECTION_NAME} already contains {existing:,} documents. "
                "Replace them? (yes/no): "
            ).strip().lower()

            if answer != "yes":
                print("Import cancelled.")
                return

            await collection.delete_many({})
            print("Existing catalog removed.")

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

        print(f"\nPrepared {len(records):,} documents.")

        batch_size = 5000

        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]

            await collection.insert_many(
                batch,
                ordered=False,
            )

            print(
                f"Inserted {min(start + batch_size, len(records)):,}"
                f"/{len(records):,}"
            )

        print("\nCreating indexes...")

        await collection.create_index(
            "article_id",
            unique=True,
        )

        await collection.create_index("name")
        await collection.create_index("category")
        await collection.create_index("department")
        await collection.create_index("colour")

        final_count = await collection.count_documents({})

        print("\n" + "=" * 60)
        print("IMPORT COMPLETE")
        print("=" * 60)
        print(f"MongoDB documents: {final_count:,}")

    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(import_catalog())