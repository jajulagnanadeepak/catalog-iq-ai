
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from dependencies import get_db

router = APIRouter(prefix="/budget", tags=["Budget Optimizer"])


class BudgetPayload(BaseModel):
    budget: float = Field(gt=0)
    categories: list[str] = Field(default_factory=list)
    priority: str = "balanced"


@router.post("", summary="Optimize a shopping budget")
async def optimize_budget(
    payload: BudgetPayload,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    priority = payload.priority.lower().strip()

    if priority not in {"value", "quality", "balanced"}:
        raise HTTPException(
            status_code=400,
            detail="Priority must be value, quality, or balanced.",
        )

    categories = list(dict.fromkeys(
        category.strip()
        for category in payload.categories
        if category.strip()
    ))

    import re

    if not categories:
        categories = ["Tops", "Footwear", "Bags"]

    regex_categories = [re.compile(f"^{re.escape(c)}$", re.IGNORECASE) for c in categories]

    products = await db["products"].find({
        "category": {"$in": regex_categories},
        "in_stock": {"$ne": False},
    }).to_list(length=500)

    # Normalize the response shape expected by the frontend.
    for product in products:
        product["id"] = str(product.pop("_id"))
        product["currency"] = product.get("currency", "USD")
        product["inStock"] = product.get("in_stock", True)
        product["originalPrice"] = product.get("original_price")

    def price_of(product):
        return float(product.get("price", 0))

    def rank_key(product):
        price = price_of(product)
        rating = float(product.get("rating", 0))

        if priority == "value":
            return (price, -rating)

        if priority == "quality":
            return (-rating, price)

        return (-(rating / max(price, 1)), price)

    # Sort products independently within each requested category.
    by_category = {category.lower(): [] for category in categories}
    for product in products:
        category_lower = str(product.get("category", "")).lower()
        price = price_of(product)

        if category_lower in by_category and 0 < price <= payload.budget:
            by_category[category_lower].append(product)

    for category in by_category:
        by_category[category].sort(key=rank_key)

    allocations = []
    selected_ids = set()
    spent = 0.0

    # Pass 1: allocate one suitable product per selected category.
    for category in categories:
        cat_products = by_category.get(category.lower(), [])
        affordable = next(
            (
                product
                for product in cat_products
                if product["id"] not in selected_ids
                and spent + price_of(product) <= payload.budget
            ),
            None,
        )

        if affordable is None:
            continue

        price = price_of(affordable)
        allocations.append({
            "category": category,
            "amount": price,
            "product": affordable,
        })
        selected_ids.add(affordable["id"])
        spent += price

    # Pass 2: spend remaining budget on additional products.
    remaining_products = sorted(
        (
            product
            for category_products in by_category.values()
            for product in category_products
            if product["id"] not in selected_ids
        ),
        key=rank_key,
    )

    for product in remaining_products:
        price = price_of(product)

        if spent + price > payload.budget:
            continue

        allocations.append({
            "category": product["category"],
            "amount": price,
            "product": product,
        })
        selected_ids.add(product["id"])
        spent += price

    spent = round(spent, 2)

    return {
        "budget": payload.budget,
        "spent": spent,
        "saved": round(max(0, payload.budget - spent), 2),
        "allocations": allocations,
    }
