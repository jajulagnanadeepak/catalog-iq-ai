
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from dependencies import get_db

router = APIRouter(
    prefix="/seasonal",
    tags=["Seasonal Recommendations"],
)

SEASON_RULES = {
    "spring": {
        "keywords": [
            "linen", "cotton", "lightweight", "breathable",
            "spring", "casual", "sage", "sky",
        ],
        "categories": {"tops", "footwear", "bags"},
        "headline": "Light layers and versatile everyday essentials for spring.",
        "weights": {"linen": 5, "lightweight": 5, "cotton": 3},
    },
    "summer": {
        "keywords": [
            "summer", "linen", "breathable", "lightweight",
            "swim", "beach", "terry", "polo",
        ],
        "categories": {"tops", "swimwear"},
        "headline": "Lightweight pieces and warm-weather essentials for summer.",
        "weights": {
            "summer": 6, "swim": 7, "beach": 5,
            "linen": 5, "breathable": 5, "lightweight": 5,
        },
    },
    "autumn": {
        "keywords": [
            "jacket", "layering", "overshirt", "chino",
            "knitwear", "wool", "olive", "autumn",
        ],
        "categories": {"outerwear", "trousers", "footwear"},
        "headline": "Layering pieces and versatile staples for autumn.",
        "weights": {
            "jacket": 6, "layering": 6, "overshirt": 5,
            "autumn": 5, "chino": 3,
        },
    },
    "winter": {
        "keywords": [
            "winter", "wool", "merino", "knitwear",
            "overcoat", "puffer", "down", "warm", "layering",
        ],
        "categories": {"outerwear"},
        "headline": "Warm layers and cold-weather essentials for winter.",
        "weights": {
            "winter": 7, "wool": 7, "merino": 7,
            "puffer": 8, "down": 7, "warm": 6,
            "overcoat": 7, "knitwear": 6,
        },
    },
}


def seasonal_score(product: dict, season: str) -> float:
    rules = SEASON_RULES[season]

    tags = product.get("tags", [])
    if not isinstance(tags, list):
        tags = []

    name = str(product.get("name", "")).lower()
    category = str(product.get("category", "")).lower()
    description = str(product.get("description", "")).lower()
    searchable_text = " ".join(
        [name, category, description]
        + [str(tag).lower() for tag in tags]
    )

    score = 0.0

    # Exact seasonal keyword matches receive stronger scores.
    for keyword, weight in rules["weights"].items():
        if keyword in searchable_text:
            score += weight

    # Relevant categories provide a smaller bonus.
    if category in rules["categories"]:
        score += 2

    # Ratings help distinguish products with similar relevance.
    try:
        score += float(product.get("rating", 0) or 0) * 0.5
    except (TypeError, ValueError):
        pass

    # Penalize products that explicitly have no stock.
    if product.get("in_stock") is False:
        score -= 100

    return score


@router.get("", summary="Get seasonal product recommendations")
async def get_seasonal_recommendations(
    season: str = Query(..., description="Spring, Summer, Autumn, or Winter"),
    limit: int = Query(8, ge=1, le=50),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    normalized_season = season.strip().lower()

    if normalized_season not in SEASON_RULES:
        return {
            "season": season,
            "headline": "Unsupported season. Choose Spring, Summer, Autumn, or Winter.",
            "items": [],
        }

    products = await db["products"].find({
        "in_stock": {"$ne": False},
        "price": {"$gt": 0},
    }).to_list(length=500)

    ranked_products = sorted(
        products,
        key=lambda product: (
            seasonal_score(product, normalized_season),
            float(product.get("rating", 0) or 0),
        ),
        reverse=True,
    )

    items = []

    for product in ranked_products[:limit]:
        product_id = str(product.pop("_id", product.get("id", "")))
        product["id"] = product_id
        product["currency"] = product.get("currency", "USD")
        product["inStock"] = product.get("in_stock", True)
        product["originalPrice"] = product.get("original_price")

        items.append(product)

    return {
        "season": normalized_season.title(),
        "headline": SEASON_RULES[normalized_season]["headline"],
        "items": items,
    }
