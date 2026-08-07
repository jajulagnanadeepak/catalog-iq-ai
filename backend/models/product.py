from typing import Optional
from pydantic import BaseModel, Field


class Product(BaseModel):
    id: str = Field(alias="_id")
    name: str
    brand: str
    category: str
    price: float
    original_price: Optional[float] = None
    rating: float
    reviews: int
    image: str
    colors: list[str] = []
    sizes: list[str] = []
    tags: list[str] = []
    description: str
    in_stock: bool = True

    model_config = {"populate_by_name": True}


class ProductInDB(BaseModel):
    """Model for MongoDB documents (id stored as _id)."""

    name: str
    brand: str
    category: str
    price: float
    original_price: Optional[float] = None
    rating: float
    reviews: int
    image: str
    colors: list[str] = []
    sizes: list[str] = []
    tags: list[str] = []
    description: str
    in_stock: bool = True
