import pickle

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from database.connection import connect_db, close_db, get_database


MODEL_NAME = "all-MiniLM-L6-v2"

INDEX_PATH = "hm_products.index"
IDS_PATH = "hm_product_ids.pkl"


print("Loading semantic search model...")

model = SentenceTransformer(MODEL_NAME)

print("Loading H&M FAISS index...")

index = faiss.read_index(INDEX_PATH)

with open(IDS_PATH, "rb") as f:
    product_ids = pickle.load(f)

print(f"✅ FAISS vectors loaded: {index.ntotal:,}")
print(f"✅ Product IDs loaded: {len(product_ids):,}")


async def semantic_search(query: str, top_k: int = 20):
    if not query or not query.strip():
        return []

    top_k = max(1, min(top_k, index.ntotal))

    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
    ).astype(np.float32)

    distances, indices = index.search(
        query_embedding,
        top_k,
    )

    article_ids = []

    for idx in indices[0]:
        if idx < 0 or idx >= len(product_ids):
            continue

        article_ids.append(product_ids[idx])

    if not article_ids:
        return []

    await connect_db()

    try:
        db = get_database()
        collection = db["catalog_products"]

        products = await collection.find(
            {
                "_id": {
                    "$in": article_ids
                }
            }
        ).to_list(length=top_k)

        product_map = {
            product["_id"]: product
            for product in products
        }

        results = []

        for rank, (idx, distance) in enumerate(
            zip(indices[0], distances[0]),
            start=1,
        ):
            if idx < 0 or idx >= len(product_ids):
                continue

            article_id = product_ids[idx]

            product = product_map.get(article_id)

            if product is None:
                continue

            product["_id"] = str(product["_id"])

            results.append(
                {
                    "rank": rank,
                    "article_id": article_id,
                    "distance": float(distance),
                    "product": product,
                }
            )

        return results

    finally:
        await close_db()