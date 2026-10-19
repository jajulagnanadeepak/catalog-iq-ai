
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from itertools import product as cartesian_product

from dependencies import get_db

router = APIRouter(prefix="/stylist", tags=["AI Stylist"])


class StylistPayload(BaseModel):
    occasion: str = "Everyday"
    style: str = "Minimal"
    bodyType: str | None = None
    budget: float = Field(default=800, gt=0)
    notes: str = ""


def score_product(product: dict, payload: StylistPayload) -> int:
    text = " ".join([
        str(product.get("name", "")),
        str(product.get("category", "")),
        str(product.get("description", "")),
        " ".join(product.get("tags", [])),
        " ".join(product.get("colors", [])),
    ]).lower()

    score = int(float(product.get("rating", 0)) * 2)
    occasion = payload.occasion.lower()
    style = payload.style.lower()
    notes = payload.notes.lower()

    if any(word in occasion for word in ["work", "office", "business"]):
        if any(word in text for word in [
            "formal", "work", "office", "leather", "knit",
            "outerwear", "smart-casual",
        ]):
            score += 5
        if any(word in text for word in ["sport", "running", "swim", "beach"]):
            score -= 5

    if any(word in occasion for word in ["evening", "wedding", "party"]):
        if any(word in text for word in [
            "formal", "premium", "leather", "classic",
        ]):
            score += 4

    if any(word in occasion for word in ["everyday", "travel"]):
        if any(word in text for word in [
            "everyday", "casual", "travel", "cotton", "waterproof",
        ]):
            score += 4

    if any(word in style for word in ["minimal", "classic"]):
        if any(word in text for word in [
            "neutral", "classic", "formal", "leather", "knit",
        ]):
            score += 3

    if any(word in style for word in ["street", "utility"]):
        if any(word in text for word in [
            "sport", "utility", "outdoor", "sneakers", "packable",
        ]):
            score += 3


    avoid_bright = any(word in notes for word in [
        "avoid bright", "no bright", "neutral colours", "neutral colors",
    ])

    if avoid_bright:
        colors = [
            str(color).strip().lower()
            for color in product.get("colors", [])
        ]

        bright_colors = {
            "red", "crimson", "neon", "orange", "yellow",
            "hot pink", "lime", "bright green", "electric blue",
        }

        if any(color in bright_colors for color in colors):
            score -= 8


    return score


def category_bonus(product: dict, payload: StylistPayload) -> int:
    category = str(product.get("category", "")).strip().lower()
    occasion = payload.occasion.lower()
    style = payload.style.lower()

    if any(word in occasion for word in ["work", "office", "business"]):
        preferred = ["tops", "trousers", "footwear", "bags", "outerwear"]
    elif any(word in occasion for word in ["evening", "wedding", "party"]):
        preferred = ["tops", "trousers", "footwear", "accessories", "outerwear"]
    elif "travel" in occasion:
        preferred = ["tops", "trousers", "footwear", "bags", "outerwear"]
    else:
        preferred = ["tops", "trousers", "footwear", "outerwear", "bags"]

    bonus = 4 if category in preferred else 0

    if category in {"electronics", "swimwear"} and any(
        word in occasion for word in ["work", "office", "business"]
    ):
        bonus -= 10

    if style == "utility" and category == "bags":
        bonus += 2

    return bonus


def category_key(product: dict) -> str:
    return str(product.get("category", "")).strip().lower()


def matches_color_preferences(product: dict, payload: StylistPayload) -> bool:
    notes = payload.notes.lower()

    avoid_bright = any(
        phrase in notes
        for phrase in [
            "avoid bright",
            "no bright",
            "neutral colours",
            "neutral colors",
        ]
    )

    if not avoid_bright:
        return True

    bright_colors = {
        "red", "crimson", "neon", "orange", "yellow",
        "hot pink", "lime", "bright green", "electric blue",
    }

    colors = {
        str(color).strip().lower()
        for color in product.get("colors", [])
    }

    return not any(color in bright_colors for color in colors)



def product_score(product: dict, payload: StylistPayload) -> tuple:
    return (
        score_product(product, payload) + category_bonus(product, payload),
        float(product.get("rating", 0)),
    )


@router.post("", summary="Generate outfit recommendations")
async def generate_stylist_looks(
    payload: StylistPayload,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    products = await db["products"].find({
        "in_stock": {"$ne": False},
        "price": {"$gt": 0, "$lte": payload.budget},
    }).to_list(length=500)

    for product in products:
        product["id"] = str(product.pop("_id"))
        product["currency"] = product.get("currency", "USD")
        product["inStock"] = product.get("in_stock", True)
        product["originalPrice"] = product.get("original_price")

    if not products:
        return [{
            "id": "look-1",
            "title": "No matching products",
            "summary": "No in-stock products fit this budget. Try increasing it.",
            "items": [],
            "total": 0,
        }]

    occasion = payload.occasion.lower()
    is_work = any(
        word in occasion for word in ["work", "office", "business"]
    )

    # Build a ranked catalog without changing the underlying dataset.
    ranked = sorted(
        products,
        key=lambda product: product_score(product, payload),
        reverse=True,
    )

    print("STYLIST REQUEST:", payload.model_dump())

    for product in ranked[:10]:
        print(
            "STYLIST PRODUCT:",
            product.get("name"),
            "| category:", product.get("category"),
            "| price:", product.get("price"),
            "| score:", product_score(product, payload)[0],
        )


    looks = []

    required_categories = ["tops", "trousers", "footwear"]
    is_work = any(
        word in payload.occasion.lower()
        for word in ["work", "office", "business"]
    )

    # Create candidate lists for every core outfit category.
    category_candidates = {}

    for category in required_categories:
        category_candidates[category] = sorted(
            [
                p for p in products
                if category_key(p) == category
                and float(p.get("price", 0)) > 0
                and matches_color_preferences(p, payload)
            ],
            key=lambda p: product_score(p, payload),
            reverse=True,
        )

    # Generate valid outfits by trying combinations, not greedily
    # selecting the most expensive top or trousers first.
    combinations = []

    if all(category_candidates[c] for c in required_categories):
        for top, trousers, footwear in cartesian_product(
            category_candidates["tops"],
            category_candidates["trousers"],
            category_candidates["footwear"],
        ):
            items = [top, trousers, footwear]
            total = sum(float(p.get("price", 0)) for p in items)

            if total > payload.budget:
                continue

            ids = [p["id"] for p in items]
            if len(ids) != len(set(ids)):
                continue

            score = sum(product_score(p, payload)[0] for p in items)
            combinations.append((score, total, items))

    combinations.sort(
        key=lambda entry: (entry[0], -entry[1]),
        reverse=True,
    )

    # Choose up to two distinct complete outfits.
    used_outfit_ids = set()

    for index in range(2):
        chosen_combination = next(
            (
                combination for combination in combinations
                if tuple(sorted(p["id"] for p in combination[2]))
                not in used_outfit_ids
            ),
            None,
        )

        if chosen_combination is None:
            looks.append({
                "id": f"look-{index + 1}",
                "title": (
                    f"Refined {payload.occasion} look"
                    if index == 0
                    else f"Alternative {payload.style} look"
                ),
                "summary": (
                    "No additional distinct complete outfit fits "
                    "your budget using the available products."
                ),
                "items": [],
                "total": 0,
            })
            continue

        _, total, selected = chosen_combination
        outfit_key = tuple(sorted(p["id"] for p in selected))
        used_outfit_ids.add(outfit_key)

        looks.append({
            "id": f"look-{index + 1}",
            "title": (
                f"Refined {payload.occasion} look"
                if index == 0
                else f"Alternative {payload.style} look"
            ),
            "summary": (
                "Complete outfit with a top, trousers, and footwear, "
                "selected from in-stock products within your budget."
            ),
            "items": selected,
            "total": round(total, 2),
        })

    return looks
