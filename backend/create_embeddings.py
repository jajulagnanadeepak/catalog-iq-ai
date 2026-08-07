import asyncio
import pickle

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from config import settings
from database.connection import connect_db, close_db, get_database


async def create_embeddings():
    print("=" * 60)
    print("CatalogIQ Semantic Search")
    print("=" * 60)

    print(f"MongoDB URL : {settings.mongodb_url}")
    print(f"Database    : {settings.database_name}")

    print("\nLoading Sentence Transformer Model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("✅ Model Loaded")

    print("\nConnecting to MongoDB...")
    await connect_db()

    try:
        db = get_database()

        print("\nChecking available collections...")

        collections = await db.list_collection_names()

        if not collections:
            print("❌ No collections found in this database.")
            return

        print("\nCollections Found:")
        for collection_name in collections:
            count = await db[collection_name].count_documents({})
            print(f"   • {collection_name} : {count} documents")

        # --------------------------------------------------
        # CHANGE THIS ONLY IF YOUR COLLECTION NAME IS DIFFERENT
        # --------------------------------------------------
        products_collection = db["Products"]

        count = await products_collection.count_documents({})

        print(f"\nProducts Collection Count : {count}")

        if count == 0:
            print("\n❌ Products collection is empty.")
            print("Please run seed.py first.")
            return

        print("\nLoading products...")

        products = await products_collection.find().to_list(length=None)

        print(f"✅ Loaded {len(products)} products")

        texts = []
        product_ids = []

        print("\nPreparing text for embeddings...")

        for product in products:

            text = " ".join(
                [
                    str(product.get("name", "")),
                    str(product.get("brand", "")),
                    str(product.get("category", "")),
                    str(product.get("product_type", "")),
                    str(product.get("department", "")),
                    str(product.get("section", "")),
                    str(product.get("garment_group", "")),
                    str(product.get("colour", "")),
                    str(product.get("description", "")),
                ]
            )

            texts.append(text)
            product_ids.append(str(product["_id"]))

        print(f"Prepared {len(texts)} text documents.")

        print("\nGenerating embeddings...")

        embeddings = model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=True
        )

        embeddings = embeddings.astype(np.float32)

        print(f"Embedding Shape : {embeddings.shape}")

        dimension = embeddings.shape[1]

        print("\nCreating FAISS Index...")

        index = faiss.IndexFlatL2(dimension)

        index.add(embeddings)

        print(f"✅ Stored {index.ntotal} vectors")

        print("\nSaving index...")

        faiss.write_index(index, "products.index")

        with open("product_ids.pkl", "wb") as f:
            pickle.dump(product_ids, f)

        print("✅ products.index saved")
        print("✅ product_ids.pkl saved")

        print("\n🎉 Semantic Search Setup Complete!")

    except Exception as e:
        print("\n❌ ERROR")
        print(type(e).__name__)
        print(e)

    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(create_embeddings())