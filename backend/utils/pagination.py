from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class Paginated(BaseModel, Generic[T]):
    """Generic paginated response — mirrors the TypeScript Paginated<T> type."""

    items: list[T]
    page: int
    page_size: int
    total: int


def paginate(items: list, page: int = 1, page_size: int = 8) -> dict:
    """Slice a list into a page and return pagination metadata."""
    start = (page - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "page": page,
        "page_size": page_size,
        "total": len(items),
    }
