from pymongo import MongoClient
from dotenv import load_dotenv
import pandas as pd
import os

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    print("❌ MONGO_URI not found in .env file")
    exit()

print("🔄 Connecting to MongoDB...")

client = MongoClient(MONGO_URI)

# Test the connection
client.admin.command("ping")
print("✅ Connected to MongoDB!")

db = client["CatalogIQ"]
products = db["Products"]

# Delete existing products
products.delete_many({})
print("🗑 Old products deleted.")

# Read CSV
df = pd.read_csv("articles.csv")

records = []

for _, row in df.iterrows():
    records.append({
        "product_id": str(row["article_id"]),
        "name": row["prod_name"],
        "category": row["product_type_name"],
        "department": row["department_name"],
        "description": row["detail_desc"] if pd.notna(row["detail_desc"]) else ""
    })

print(f"📦 Inserting {len(records)} products...")

products.insert_many(records)

products.create_index("product_id")

print("✅ Import completed successfully!")
print(f"🎉 {len(records)} products inserted.")