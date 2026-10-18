import pytest

from services.semantic_reranker import SemanticReranker


@pytest.fixture
def reranker():
    return SemanticReranker()


def test_linen_summer_product_scores_above_generic_tee(reranker):
    linen_shirt = {
        "name": "Linen Relaxed Shirt",
        "product_type": "Shirt",
        "category": "Garment Upper body",
        "department": "Tops Woven",
        "section": "Summer Collection",
        "garment_group": "Blouses",
        "description": "Shirt in an airy linen weave.",
    }

    generic_tee = {
        "name": "Summer Price Tee",
        "product_type": "T-shirt",
        "category": "Garment Upper body",
        "department": "Jersey Fancy",
        "section": "Casual",
        "garment_group": "Jersey Fancy",
        "description": "T-shirt in soft cotton jersey.",
    }

    query = "linen shirt for summer"

    linen_score = reranker._query_match_score(query, linen_shirt)
    tee_score = reranker._query_match_score(query, generic_tee)

    assert linen_score > tee_score


def test_query_without_fabric_or_season_has_zero_match_score(reranker):
    product = {
        "name": "Linen Shirt",
        "product_type": "Shirt",
        "description": "An airy linen shirt.",
    }

    assert reranker._query_match_score("shirt for work", product) == 0.0


def test_reason_explains_linen_and_summer_match(reranker):
    product = {
        "name": "Linen Relaxed Shirt",
        "product_type": "Shirt",
        "category": "Garment Upper body",
        "department": "Tops Woven",
        "section": "Summer Collection",
        "garment_group": "Blouses",
        "description": "Shirt in an airy linen weave.",
    }

    reason = reranker._build_reason(
        query="linen shirt for summer",
        product=product,
        attributes={"category": "tops"},
        session_intent=None,
    )

    assert "linen preference" in reason
    assert "relevant to summer" in reason


def test_sneaker_query_excludes_outerwear_even_with_outerwear_session(reranker):
    results = [
        {
            "article_id": "TEST_SNEAKER_001",
            "distance": 0.30,
            "product": {
                "name": "White Everyday Sneakers",
                "product_type": "Sneakers",
                "category": "Garment and Shoe",
                "colour": "White",
                "department": "Shoes",
                "section": "Ladies Shoes",
                "garment_group": "Shoes",
                "description": "White casual sneakers for everyday wear.",
            },
        },
        {
            "article_id": "TEST_JACKET_001",
            "distance": 0.20,
            "product": {
                "name": "White Rain Jacket",
                "product_type": "Jacket",
                "category": "Garment Upper body",
                "colour": "White",
                "department": "Ladies Outerwear",
                "section": "Ladies Outerwear",
                "garment_group": "Outdoor",
                "description": "White waterproof jacket for rainy weather.",
            },
        },
    ]

    ranked = reranker.rerank(
        query="Find white sneakers for everyday use",
        results=results,
        limit=5,
        session_intent={"primary_category": "outerwear"},
    )

    assert ranked
    assert all(
        reranker._infer_product_category(item["product"]) == "footwear"
        for item in ranked
    )
    assert any(
        item["product"]["name"] == "White Everyday Sneakers"
        for item in ranked
    )
