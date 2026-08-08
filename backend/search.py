import pickle

import faiss
import numpy as np
import asyncio

from bson import ObjectId

from database.connection import connect_db, close_db, get_database
from sentence_transformers import SentenceTransformer

print("Loading AI Model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

print("✅ AI Model Loaded")
print("\nLoading FAISS Index...")

index = faiss.read_index("products.index")

print("✅ FAISS Index Loaded")
print("\nLoading Product IDs...")

with open("product_ids.pkl", "rb") as f:
    product_ids = pickle.load(f)

print(f"✅ Loaded {len(product_ids)} Product IDs")

async def semantic_search(query, top_k=20):

    print("\nSearching for:", query)

    # Step 1: Convert query into embedding
    query_embedding = model.encode(
        [query],
        convert_to_numpy=True
    )

    query_embedding = query_embedding.astype(np.float32)

    print("Embedding Shape:", query_embedding.shape)

    # Step 2: Search FAISS
    print("\nSearching FAISS...")

    distances, indices = index.search(
        query_embedding,
        top_k
    )

    print("\nDistances:")
    print(distances)

    print("\nIndices:")
    print(indices)

    # Step 3: Convert vector positions to MongoDB IDs
    print("\nConverting Vector Positions to MongoDB IDs...")

    mongo_ids = []

    for idx in indices[0]:
        mongo_ids.append(product_ids[idx])

    print("\nMongoDB Product IDs:")

    for pid in mongo_ids:
        print(pid)

    # Step 4: Connect to MongoDB
    print("\nConnecting to MongoDB...")

    await connect_db()

    db = get_database()

    products_collection = db["Products"]

    # Step 5: Fetch complete product details
    products = []

    print("\nFetching Product Details...\n")

    for pid in mongo_ids:

        product = await products_collection.find_one(
            {"_id": ObjectId(pid)}
        )

        if product:

            # Convert ObjectId into string
            product["_id"] = str(product["_id"])

            products.append(product)

    await close_db()

    # Step 6: Display products
    print("=" * 60)
    print("Top Matching Products")
    print("=" * 60)

    for i, product in enumerate(products, start=1):

        print(f"\nProduct {i}")

        print("ID          :", product.get("_id"))
        print("Name        :", product.get("name"))
        print("Category    :", product.get("category"))
        print("Type        :", product.get("product_type"))
        print("Department  :", product.get("department"))
        print("Colour      :", product.get("colour"))
        print("Description :", product.get("description"))

        print("-" * 60)

    return products

if __name__ == "__main__":

    asyncio.run(
        semantic_search("Need black running shoes")
    )
