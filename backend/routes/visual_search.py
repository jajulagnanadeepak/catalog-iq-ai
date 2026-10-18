from __future__ import annotations

from io import BytesIO
from functools import lru_cache

import httpx
import numpy as np
import torch
from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from transformers import CLIPModel, CLIPProcessor

from database.connection import connect_db, close_db, get_database


router = APIRouter(tags=["Visual Search"])

MODEL_NAME = "openai/clip-vit-base-patch32"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_CATALOG_IMAGES = 100
TOP_K = 8


@lru_cache(maxsize=1)
def load_clip():
    processor = CLIPProcessor.from_pretrained(MODEL_NAME)
    model = CLIPModel.from_pretrained(MODEL_NAME)
    model.eval()
    return processor, model




def image_embedding(image: Image.Image, processor, model) -> np.ndarray:
    inputs = processor(
        images=image.convert("RGB"),
        return_tensors="pt",
    )

    with torch.inference_mode():
        vision_output = model.vision_model(
            pixel_values=inputs["pixel_values"]
        )

        # CLIP's pooled vision features are projected into the
        # shared image/text embedding space.
        pooled_features = vision_output.pooler_output
        features = model.visual_projection(pooled_features)

        # Normalize embeddings so dot product gives cosine similarity.
        features = features / features.norm(
            dim=-1, keepdim=True
        ).clamp(min=1e-12)

    return features.cpu().numpy()[0].astype(np.float32)




@router.post("/visual-search")
async def visual_search(image: UploadFile = File(...)):
    content_type = (image.content_type or "").lower()
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(
            status_code=415,
            detail="Upload a JPG, PNG, or WebP image.",
        )

    data = await image.read(MAX_IMAGE_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 8 MB or smaller.")

    try:
        with Image.open(BytesIO(data)) as uploaded:
            if uploaded.format not in ALLOWED_FORMATS:
                raise HTTPException(
                    status_code=415,
                    detail="Upload a JPG, PNG, or WebP image.",
                )
            uploaded.load()
            uploaded_image = uploaded.convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image.")

    processor, model = load_clip()
    query_vector = image_embedding(uploaded_image, processor, model)

    await connect_db()
    try:
        collection = get_database()["products"]
        products = await collection.find(
            {"image": {"$type": "string", "$ne": ""}},
            {
                "_id": 1,
                "name": 1,
                "title": 1,
                "category": 1,
                "price": 1,
                "image": 1,
                "brand": 1,
                "description": 1,
                "currency": 1,
                "rating": 1,
                "reviews": 1,
                "in_stock": 1,
            },
        ).limit(MAX_CATALOG_IMAGES).to_list(length=MAX_CATALOG_IMAGES)
    finally:
        await close_db()

    if not products:
        raise HTTPException(
            status_code=503,
            detail="No catalog products with images are available.",
        )

    candidates = []
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        for product in products:
            try:
                response = await client.get(product["image"])
                response.raise_for_status()
                if not response.headers.get("content-type", "").lower().startswith("image/"):
                    continue
                with Image.open(BytesIO(response.content)) as catalog_image:
                    catalog_image.load()
                    vector = image_embedding(catalog_image, processor, model)
                score = float(np.dot(query_vector, vector))
                candidates.append((score, product))
            except (httpx.HTTPError, UnidentifiedImageError, OSError, ValueError):
                continue

    if not candidates:
        raise HTTPException(
            status_code=503,
            detail="Catalog images could not be loaded. Please try again later.",
        )

    candidates.sort(key=lambda item: item[0], reverse=True)

    items = []
    for score, product in candidates[:TOP_K]:
        product_id = str(product.get("_id", ""))
        name = product.get("name") or product.get("title")
        price = product.get("price")

        if not product_id or not name or not isinstance(price, (int, float)):
            continue

        items.append({
            "id": product_id,
            "name": name,
            "brand": product.get("brand", "Unknown brand"),
            "category": product.get("category", "Uncategorized"),
            "description": product.get("description", ""),
            "image": product.get("image", ""),
            "price": price,
            "currency": product.get("currency", "USD"),
            "rating": product.get("rating", 0),
            "reviews": product.get("reviews", 0),
            "colors": [],
            "sizes": [],
            "tags": [],
            "inStock": product.get("in_stock", True),
            "similarity": round(score, 4),
        })

    return {
        "detected": [],
        "items": items,
    }
