from typing import Optional
from pydantic import BaseModel, Field


class Product(BaseModel):
    id: str = Field(alias="_id")
    name: str
    brand: str
    category: str
    price: float
    currency: str = "USD"
    original_price: Optional[float] = None
    rating: float
    reviews: int
    image: str
    colors: list[str] = Field(default_factory=list)
    sizes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    description: str
    in_stock: bool = True

    model_config = {"populate_by_name": True}


class ProductInDB(BaseModel):
    """Model for MongoDB documents."""

    name: str
    brand: str
    category: str
    price: float
    currency: str = "USD"
    original_price: Optional[float] = None
    rating: float
    reviews: int
    image: str
    colors: list[str] = Field(default_factory=list)
    sizes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    description: str
    in_stock: bool = True