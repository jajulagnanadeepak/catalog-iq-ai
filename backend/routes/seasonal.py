
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from dependencies import get_db

router = APIRouter(prefix="/seasonal", tags=["Seasonal Recommendations"])



SEASON_RULES = {
    "spring": {
        "keywords": [
            "spring", "linen", "cotton", "lightweight",
            "casual", "sage", "sky", "breathable",
        ],
        "categories": {"tops", "footwear", "bags", "accessories"},
        "headline": "Light layers and versatile everyday essentials for spring.",
    },
    "summer": {
        "keywords": [
            "summer", "linen", "lightweight", "breathable",
            "cotton", "polo", "swim", "beach",
        ],
        "categories": {"tops", "footwear", "swimwear"},
        "headline": "Lightweight pieces and warm-weather essentials for summer.",
    },
    "autumn": {
        "keywords": [
            "autumn", "fall", "layering", "knitwear",
            "jacket", "wool", "overshirt", "olive",
        ],
        "categories": {"tops", "footwear", "outerwear", "bags"},
        "headline": "Layering pieces and versatile staples for autumn.",
    },
    "winter": {
        "keywords": [
            "winter", "wool", "knitwear", "merino",
            "overcoat", "puffer", "warm", "layering",
            "down", "turtleneck", "insulated",
        ],
        "categories": {"tops", "footwear", "outerwear"},
        "headline": "Warm layers and cold-weather essentials for winter.",
    },
}




def seasonal_score(product: dict, season: str) -> float:
    rules = SEASON_RULES[season]

    name = str(product.get("name", "")).lower()
    category = str(product.get("category", "")).strip().lower()
    description = str(product.get("description", "")).lower()
    tags = product.get("tags", [])
    colors = product.get("colors", [])

    searchable_text = " ".join([
        name,
        category,
        description,
        " ".join(str(tag) for tag in tags),
        " ".join(str(color) for color in colors),
    ]).lower()

    # General seasonal relevance
    score = sum(
        2 for keyword in rules["keywords"]
        if keyword in searchable_text
    )

    # Give stronger signals to products specifically suited
    # to the selected season.
    seasonal_terms = {
        "spring": {
            "linen": 4, "lightweight": 4, "cotton": 2,
            "casual": 1,
        },
        "summer": {
            "swim": 7, "beach": 5, "linen": 5,
            "breathable": 5, "lightweight": 5,
            "polo": 3, "summer": 5,
        },
        "autumn": {
            "layering": 5, "overshirt": 5, "jacket": 4,
            "knitwear": 4, "wool": 3,
        },
        "winter": {
            "overcoat": 7, "puffer": 7, "down": 6,
            "wool": 5, "merino": 5, "turtleneck": 5,
            "knitwear": 5, "warm": 5, "winter": 5,
        },
    }

    score += sum(
        weight
        for term, weight in seasonal_terms[season].items()
        if term in searchable_text
    )

    # Category relevance
    if category in rules["categories"]:
        score += 3

    # Penalize clearly off-season items.

# Penalize clearly off-season items.

    # Penalize clearly off-season items.
    if season == "summer" and any(
        term in searchable_text
        for term in (
            "overcoat",
            "puffer",
            "down jacket",
            "turtleneck",
            "merino",
            "wool",
            "sweatshirt",
            "winter",
        )
    ):
        score -= 15

    if season == "winter" and any(
        term in searchable_text
        for term in ("swim shorts", "swimwear", "bikini")
    ):
        score -= 10

    # Ratings should break ties, not dominate seasonal relevance.
    score += float(product.get("rating", 0)) * 0.25

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

    for product in products:
        product["id"] = str(product.pop("_id"))
        product["currency"] = product.get("currency", "USD")
        product["inStock"] = product.get("in_stock", True)
        product["originalPrice"] = product.get("original_price")

    ranked_products = sorted(
        products,
        key=lambda product: (
            seasonal_score(product, normalized_season),
            float(product.get("rating", 0)),
        ),
        reverse=True,
    )

    return {
        "season": normalized_season.title(),
        "headline": SEASON_RULES[normalized_season]["headline"],
        "items": ranked_products[:limit],
    }
