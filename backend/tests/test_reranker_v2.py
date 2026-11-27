"""S1 + S2 reranker behaviour on fixture products (no DB, no FAISS)."""

import pytest

from services.semantic_reranker import SemanticReranker
from services.semantic_reranker_v2 import SemanticRerankerV2

V1_ITEM_KEYS = {
    "rank", "article_id", "score", "semantic_score", "keyword_score",
    "attribute_score", "intent_score", "distance", "reason", "product",
}


def make(article_id, name, product_type, group, colour="Black",
         section="Womens Everyday Collection", distance=0.5, department="Jersey"):
    return {
        "rank": 0,
        "article_id": article_id,
        "distance": distance,
        "product": {
            "_id": article_id, "article_id": article_id, "name": name,
            "product_type": product_type, "category": group,
            "department": department, "section": section,
            "garment_group": "Jersey Fancy", "colour": colour, "description": "",
        },
    }


def candidates(*specs):
    out = []
    for i, spec in enumerate(specs):
        item = make(*spec) if isinstance(spec, tuple) else spec
        item["rank"] = i + 1
        out.append(item)
    return out


def types(results):
    return [r["product"]["product_type"] for r in results]


@pytest.fixture
def v2():
    return SemanticRerankerV2()


# ---------------------------------------------------------------- S1 product side

@pytest.mark.parametrize(
    "product_type, group, section, expected",
    [
        ("Dress", "Garment Full body", "Womens Swimwear, beachwear", "dresses"),
        ("Vest top", "Garment Upper body", "Womens Nightwear, Socks & Tigh", "tops"),
        ("Hoodie", "Garment Upper body", "Divided", "hoodies"),
        ("Skirt", "Garment Lower body", "Divided", "skirts"),
        ("Jumpsuit/Playsuit", "Garment Full body", "Divided", "jumpsuits"),
        ("Polo shirt", "Garment Upper body", "Menswear", "tops"),
        ("Leggings/Tights", "Garment Lower body", "Ladies Sport", "trousers"),
        ("Scarf", "Accessories", "Accessories", "accessories"),
        ("Other shoe", "Shoes", "Womens Shoes", "footwear"),
        ("Ballerinas", "Shoes", "Womens Shoes", "footwear"),
        ("Bikini top", "Swimwear", "Womens Swimwear, beachwear", "swimwear"),
        ("Sneakers", "Shoes", "Mens Shoes", "footwear"),
        ("Jacket", "Garment Upper body", "Menswear", "outerwear"),
        ("Sweater", "Garment Upper body", "Womens Nightwear, Socks & Tigh", "knitwear"),
        ("Bag", "Accessories", "Womens Swimwear, beachwear", "bags"),
        # unknown type -> product-group fallback, then None
        ("Something new", "Shoes", "", "footwear"),
        ("Unknown", "Unknown", "", None),
    ],
)
def test_product_category_from_type_not_section(v2, product_type, group, section, expected):
    product = make("1", "x", product_type, group, section=section)["product"]
    assert v2._infer_product_category(product) == expected


# ---------------------------------------------------------------- S1 query side

def test_bikini_top_returns_swimwear_not_tops(v2):
    pool = candidates(
        ("1", "Tee", "T-shirt", "Garment Upper body", "Pink", "Divided", 0.30),
        ("2", "Tri bikini", "Bikini top", "Swimwear", "Pink", "Womens Swimwear, beachwear", 0.40),
        ("3", "Bandeau", "Bikini top", "Swimwear", "Red", "Womens Swimwear, beachwear", 0.45),
        ("4", "Bottoms", "Swimwear bottom", "Swimwear", "Pink", "Womens Swimwear, beachwear", 0.35),
    )
    out = v2.rerank("pink bikini top", pool, limit=10)
    assert types(out)[:2] == ["Bikini top", "Bikini top"]
    assert "T-shirt" not in types(out)  # tops are outside the swimwear category
    # v1 baseline: the parser picks "tops", so swimwear is filtered out
    v1_out = SemanticReranker().rerank("pink bikini top", pool, limit=10)
    assert "Bikini top" not in types(v1_out)


def test_specific_types_first_then_broad_category_backfill(v2):
    pool = candidates(
        make("1", "Slim trousers", "Trousers", "Garment Lower body", "White", distance=0.10),
        make("2", "Wide trousers", "Trousers", "Garment Lower body", "White", distance=0.12),
        make("3", "Yoga leggings", "Leggings/Tights", "Garment Lower body", "White", distance=0.60),
        make("4", "Basic leggings", "Leggings/Tights", "Garment Lower body", "Black", distance=0.70),
        make("5", "Tee", "T-shirt", "Garment Upper body", "White", distance=0.05),
    )
    out = v2.rerank("white leggings", pool, limit=10)
    assert types(out) == ["Leggings/Tights", "Leggings/Tights", "Trousers", "Trousers"]


def test_polo_shirts_are_not_filtered_out(v2):
    pool = candidates(
        ("1", "Tee", "T-shirt", "Garment Upper body", "Red", "Menswear", 0.2),
        ("2", "Pique polo", "Polo shirt", "Garment Upper body", "Red", "Menswear", 0.5),
    )
    assert types(v2.rerank("red polo shirt for men", pool))[0] == "Polo shirt"
    assert "Polo shirt" not in types(SemanticReranker().rerank("red polo shirt for men", pool))


def outerwear_pool():
    return candidates(
        make("blz", "Blazer", "Blazer", "Garment Upper body", "Beige", distance=0.10),
        make("jkt", "Trenchcoat", "Jacket", "Garment Upper body", "Beige", distance=0.20),
        make("cot", "Trench coat", "Coat", "Garment Upper body", "Beige", distance=0.30),
        make("cot2", "Wool coat", "Coat", "Garment Upper body", "Black", distance=0.40),
        make("tee", "Tee", "T-shirt", "Garment Upper body", "Beige", distance=0.05),
    )


def test_trench_coat_matches_coat_and_jacket_before_backfill(v2):
    out = v2.rerank("beige trench coat", outerwear_pool())
    ids = [r["article_id"] for r in out]
    # Jacket and Coat are both specific matches; the blazer is outerwear backfill
    assert set(ids[:3]) == {"jkt", "cot", "cot2"}
    assert ids[3] == "blz"
    assert "tee" not in ids
    assert {"Jacket", "Coat"} <= set(types(out[:2]))


def test_coat_query_still_prefers_coat_type(v2):
    out = v2.rerank("black coat", outerwear_pool())
    assert types(out)[:2] == ["Coat", "Coat"]
    assert set(types(out)[2:]) == {"Jacket", "Blazer"}  # backfill only


def test_jacket_query_unchanged(v2):
    assert types(v2.rerank("beige jacket", outerwear_pool()))[0] == "Jacket"


def test_v1_trench_behaviour_unchanged():
    from services.query_parser import QueryParser

    assert QueryParser.extract("beige trench coat")["category"] == "outerwear"
    # v1 has no type specificity: pure score order within outerwear
    out = SemanticReranker().rerank("beige trench coat", outerwear_pool())
    assert [r["article_id"] for r in out] == [
        r["article_id"] for r in sorted(out, key=lambda r: -r["score"])
    ]
    assert "tee" not in [r["article_id"] for r in out]


def test_broad_category_behaves_like_v1(v2):
    """'shoes' sets only the category: same products and order as v1."""
    pool = candidates(
        ("1", "Runner", "Sneakers", "Shoes", "White", "Mens Shoes", 0.2),
        ("2", "Chelsea", "Boots", "Shoes", "Black", "Mens Shoes", 0.3),
        ("3", "Cap", "Cap/peaked", "Accessories", "Black", "Menswear", 0.1),
        ("4", "Slide", "Sandals", "Shoes", "Black", "Mens Shoes", 0.4),
    )
    v1_out = SemanticReranker().rerank("comfortable running shoes", pool)
    v2_out = v2.rerank("comfortable running shoes", pool)
    assert [r["article_id"] for r in v2_out] == [r["article_id"] for r in v1_out]


# ---------------------------------------------------------------- S2 diversity + backfill

def no_category_pool(n_dresses=6, n_other=0):
    """Dresses are closer (better) than tops. 'clothes for a party' has no
    category, so it takes the diversity path."""
    pool = [make("d%d" % i, "Dress %d" % i, "Dress", "Garment Full body", distance=0.1 + i / 100)
            for i in range(n_dresses)]
    pool += [make("t%d" % i, "Top %d" % i, "Top", "Garment Upper body", distance=0.5 + i / 100)
             for i in range(n_other)]
    return candidates(*pool)


def test_backfill_fills_to_top_k_when_cap_would_underfill(v2):
    pool = no_category_pool(n_dresses=8, n_other=1)
    out = v2.rerank("clothes for a party", pool, limit=5)
    assert len(out) == 5
    # v1: cap = 1 per category at top_k=5 -> one dress + one top
    assert len(SemanticReranker().rerank("clothes for a party", pool, limit=5)) == 2


def test_cap_still_applies_when_enough_diverse_candidates(v2):
    pool = no_category_pool(n_dresses=8, n_other=8)
    out = v2.rerank("clothes for a party", pool, limit=10)
    # Cap 3 per category: d0-d2 and t0-t2 are taken first (diversity keeps
    # the tops in), then the 4 best skipped items (d3-d6) backfill.
    assert sorted(r["article_id"] for r in out) == sorted(
        ["d0", "d1", "d2", "d3", "d4", "d5", "d6", "t0", "t1", "t2"]
    )
    # v1 stops at the cap: 3 dresses + 3 tops
    assert len(SemanticReranker().rerank("clothes for a party", pool, limit=10)) == 6


@pytest.mark.parametrize("top_k", [1, 2, 5, 10, 50])
def test_respects_top_k(v2, top_k):
    pool = no_category_pool(n_dresses=20, n_other=20)
    out = v2.rerank("clothes for a party", pool, limit=top_k)
    assert len(out) == min(top_k, 40)
    assert [r["rank"] for r in out] == list(range(1, len(out) + 1))


def test_fewer_candidates_than_top_k_returns_all_eligible(v2):
    pool = no_category_pool(n_dresses=3)
    assert len(v2.rerank("clothes for a party", pool, limit=10)) == 3


def test_no_duplicates_including_same_style_variants(v2):
    pool = no_category_pool(n_dresses=6, n_other=6)
    pool.append(make("dup", "Dress 0", "Dress", "Garment Full body", distance=0.9))
    out = v2.rerank("clothes for a party", pool, limit=50)
    ids = [r["article_id"] for r in out]
    assert len(ids) == len(set(ids))
    assert "dup" not in ids  # same name + type as d0 -> deduplicated


def test_deterministic_ordering_and_tie_break_by_faiss_rank(v2):
    pool = candidates(*[make(str(i), "Same %d" % i, "Dress", "Garment Full body", distance=0.5)
                        for i in range(6)])
    first = [r["article_id"] for r in v2.rerank("black dress", pool)]
    for _ in range(5):
        assert [r["article_id"] for r in v2.rerank("black dress", pool)] == first
    assert first == [str(i) for i in range(6)]


def test_empty_inputs(v2):
    assert v2.rerank("black dress", [], limit=10) == []
    assert v2.rerank("black dress", no_category_pool(2), limit=0) == []


def test_response_items_have_v1_shape(v2):
    pool = no_category_pool(n_dresses=2)
    v1_item = SemanticReranker().rerank("clothes for a party", pool)[0]
    v2_item = v2.rerank("clothes for a party", pool)[0]
    assert set(v1_item) == set(v2_item) == V1_ITEM_KEYS
    assert not any(k.startswith("_") for k in v2_item)
