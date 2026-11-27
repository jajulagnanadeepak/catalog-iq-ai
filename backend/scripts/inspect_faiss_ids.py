import pickle
import faiss

with open("product_ids.pkl", "rb") as f:
    ids = pickle.load(f)

index = faiss.read_index("products.index")

print("FAISS vectors:", index.ntotal)
print("FAISS dimension:", index.d)
print("FAISS metric:", index.metric_type)

print("\nProduct IDs:", len(ids))
print("First 10 IDs:")
for x in ids[:10]:
    print(x)

print("\nLast 5 IDs:")
for x in ids[-5:]:
    print(x)