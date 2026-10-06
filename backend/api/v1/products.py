from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


@router.get(
    "",
    summary="List products",
    description="Returns a paginated, filtered, and sorted list of catalog products.",
)
async def list_products(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(8, ge=1, le=100, alias="pageSize"),
    category: Optional[str] = Query(
        None,
        description="Filter by category (e.g. Outerwear)",
    ),
    min_price: Optional[float] = Query(
        None,
        alias="minPrice",
        ge=0,
    ),
    max_price: Optional[float] = Query(
        None,
        alias="maxPrice",
        ge=0,
    ),
    min_rating: Optional[float] = Query(
        None,
        alias="minRating",
        ge=0,
        le=5,
    ),
    sort: Optional[str] = Query(
        None,
        description="Sort order: relevance | price-asc | price-desc | rating",
    ),
):
    service = ProductService()

    return await service.list_products(
        page=page,
        page_size=page_size,
        category=category,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        sort=sort,
    )


@router.get(
    "/{product_id}",
    summary="Get product by ID",
    description="Fetch a single product by its ID.",
)
async def get_product(product_id: str):
    service = ProductService()

    product = await service.get_product(product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return product.model_dump(by_alias=False)