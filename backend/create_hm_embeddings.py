import asyncio
import pickle

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from database.connection import connect_db, close_db, get_database


MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION_NAME = "catalog_products"

INDEX_PATH = "hm_products.index"
IDS_PATH = "hm_product_ids.pkl"


async def create_embeddings():
    print("=" * 60)
    print("CatalogIQ H&M Semantic Search Index")
    print("=" * 60)

    print("\nLoading Sentence Transformer...")
    model = SentenceTransformer(MODEL_NAME)
    print("✅ Model Loaded")

    await connect_db()

    try:
        db = get_database()
        collection = db[COLLECTION_NAME]

        count = await collection.count_documents({})

        print(f"\nCatalog documents: {count:,}")

        if count == 0:
            raise RuntimeError(
                "catalog_products is empty. Run the H&M import first."
            )

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

        print("\nSaving index...")

        faiss.write_index(index, INDEX_PATH)

        with open(IDS_PATH, "wb") as f:
            pickle.dump(product_ids, f)

        print(f"✅ Saved: {INDEX_PATH}")
        print(f"✅ Saved: {IDS_PATH}")

        print("\nVerifying mapping...")

        print("First 5 mappings:")

        for i in range(5):
            print(
                f"FAISS {i} -> article_id {product_ids[i]}"
            )

        print("\n" + "=" * 60)
        print("H&M FAISS INDEX COMPLETE")
        print("=" * 60)

    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(create_embeddings())