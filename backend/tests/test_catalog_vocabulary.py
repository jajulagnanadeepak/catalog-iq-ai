"""S1 vocabulary is consistent with itself and with the real catalogue."""

import collections
import csv
from pathlib import Path

import pytest

from services.catalog_vocabulary import (
    CATEGORIES,
    PRODUCT_TYPE_CATEGORY,
    QUERY_TERMS,
    _QUERY_TERMS,
    normalise,
)
from services.semantic_reranker import SemanticReranker
from services.semantic_reranker_v2 import SemanticRerankerV2

ARTICLES_CSV = Path(__file__).resolve().parents[2] / "articles.csv"

V1_CATEGORIES = {
    "tops", "trousers", "outerwear", "knitwear", "footwear", "bags",
    "swimwear", "nightwear",
}


def test_v1_category_names_are_kept():
    assert V1_CATEGORIES <= CATEGORIES


def test_query_term_types_all_exist_in_type_table():
    for phrase, (category, types) in QUERY_TERMS.items():
        assert category in CATEGORIES, phrase
        for t in types or ():
            assert t in PRODUCT_TYPE_CATEGORY, (phrase, t)


def test_no_phrase_is_defined_twice():
    phrases = [normalise(p) for group, _, _ in _QUERY_TERMS for p in group]
    duplicates = [p for p, n in collections.Counter(phrases).items() if n > 1]
    assert duplicates == []


@pytest.mark.skipif(not ARTICLES_CSV.exists(), reason="articles.csv not present")
def test_every_catalogue_product_type_is_mapped():
    with open(ARTICLES_CSV, encoding="utf-8", newline="") as f:
        types = {row["product_type_name"] for row in csv.DictReader(f)}

    assert len(types) == 131
    unmapped = sorted(t for t in types if normalise(t) not in PRODUCT_TYPE_CATEGORY)
    # "Unknown" is a placeholder type in the source data, deliberately unmapped.
    assert unmapped == ["Unknown"]
    stale = sorted(t for t in PRODUCT_TYPE_CATEGORY if t not in {normalise(x) for x in types})
    assert stale == []


def test_v2_agrees_with_v1_where_v1_already_mapped_by_type():
    """For every type v1 maps via product_type alone, v2 gives the same category."""
    v1, v2 = SemanticReranker(), SemanticRerankerV2()
    for product_type, v2_category in PRODUCT_TYPE_CATEGORY.items():
        v1_category = v1._infer_product_category({"product_type": product_type})
        if v1_category is not None:
            assert v1_category == v2_category, product_type
