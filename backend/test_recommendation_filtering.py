
import pytest

from models.product import Product
from services.recommendation_service import RecommendationService


def make_product(name, tags, category="Tops", description=""):
    return Product(
        id=name.lower().replace(" ", "-"),
        name=name,
        brand="Test Brand",
        category=category,
        price=100.0,
        rating=4.5,
        reviews=100,
        image="test.jpg",
        tags=tags,
        description=description,
    )


PRODUCTS = [
    make_product("Terry Polo Shirt", ["polo", "terry", "summer"]),
    make_product("Linen Relaxed Shirt", ["linen", "shirt", "summer", "casual"]),
    make_product("Cotton Crew Sweatshirt", ["sweatshirt", "cotton", "casual"]),
    make_product("Merino Turtleneck", ["merino", "turtleneck", "knitwear"]),
    make_product("Down Puffer Jacket", ["jacket", "winter"], "Outerwear"),
    make_product("Field Jacket", ["jacket", "casual"], "Outerwear"),
]


def search_products(query):
    tokens = RecommendationService._tokenize(query)
    category = RecommendationService._query_category(tokens)

    return [
        product.name
        for product in PRODUCTS
        if (
            not category
            or RecommendationService._category_matches_intent(
                product.category, category
            )
        )
        and RecommendationService._matches_query_modifiers(
            product, tokens, category
        )
    ]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (
            "shirt",
            ["Terry Polo Shirt", "Linen Relaxed Shirt"],
        ),
        (
            "polo",
            ["Terry Polo Shirt"],
        ),
        (
            "sweatshirt",
            ["Cotton Crew Sweatshirt"],
        ),
        (
            "linen shirt",
            ["Linen Relaxed Shirt"],
        ),
        (
            "jacket",
            ["Down Puffer Jacket", "Field Jacket"],
        ),
    ],
)
def test_recommendation_query_filtering(query, expected):
    assert search_products(query) == expected
