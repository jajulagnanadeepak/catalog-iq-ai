from pymongo import MongoClient
from dotenv import load_dotenv
import pandas as pd
import os

# --------------------------------------------------
# Load environment variables
# --------------------------------------------------
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise Exception("❌ MONGO_URI not found in .env file")

# --------------------------------------------------
# Connect to MongoDB Atlas
# --------------------------------------------------
print("🔄 Connecting to MongoDB Atlas...")

client = MongoClient(MONGO_URI)

# Test connection
client.admin.command("ping")

print("✅ Connected Successfully!")

# --------------------------------------------------
# Database & Collection
# --------------------------------------------------
db = client["CatalogIQ"]
products = db["Products"]

# --------------------------------------------------
# Clear old data (optional)
# --------------------------------------------------
products.delete_many({})
print("🗑 Existing products removed.")

# --------------------------------------------------
# Read CSV
# --------------------------------------------------
print("📄 Reading articles.csv...")

df = pd.read_csv("articles.csv")

print(f"📦 Found {len(df)} products.")

# --------------------------------------------------
# Convert CSV rows into MongoDB documents
# --------------------------------------------------
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

# --------------------------------------------------
# Insert Products
# --------------------------------------------------
print("🚀 Uploading products to MongoDB...")

products.insert_many(records)

# --------------------------------------------------
# Create useful indexes
# --------------------------------------------------
products.create_index("product_id", unique=True)
products.create_index("name")
products.create_index("category")
products.create_index("department")
products.create_index("colour")

print("✅ Indexes created.")

print("--------------------------------------")
print(f"🎉 Successfully Imported {len(records)} Products")
print("--------------------------------------")