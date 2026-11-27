"""S1 query parsing: catalogue vocabulary, specificity and head-noun choice."""

import pytest

from services.query_parser import QueryParser
from services.query_parser_v2 import extract_v2


def parse(q):
    a = extract_v2(q)
    return a["category"], sorted(a["product_types"]) if a["product_types"] else None


@pytest.mark.parametrize(
    "query, category, types",
    [
        # specific beats general
        ("pink bikini top for women", "swimwear", ["bikini top"]),
        ("red bikini top", "swimwear", ["bikini top"]),
        ("black top", "tops", None),
        ("red polo shirt for men", "tops", ["polo shirt"]),
        ("grey shirt for women", "tops", ["shirt"]),
        ("white t-shirt", "tops", ["t-shirt"]),
        ("tie-dye t-shirt", "tops", ["t-shirt"]),
        # categories v1 did not have
        ("black casual dress for women", "dresses", ["dress"]),
        ("summer floral dress", "dresses", ["dress"]),
        ("wedding guest dresses", "dresses", ["dress"]),
        ("popular hoodies", "hoodies", ["hoodie"]),
        ("denim skirt", "skirts", ["skirt"]),
        ("black jumpsuit", "jumpsuits", ["jumpsuit/playsuit"]),
        ("white leggings", "trousers", ["leggings/tights"]),
        ("gym leggings for women", "trousers", ["leggings/tights"]),
        ("wool scarf", "accessories", ["scarf"]),
        ("brown leather belt", "accessories", ["belt"]),
        ("winter hat for kids", "accessories",
         ["beanie", "bucket hat", "felt hat", "hat/beanie", "hat/brim", "straw hat"]),
        # synonyms
        ("swimming costume", "swimwear", ["swimsuit"]),
        ("white trainers", "footwear", ["sneakers"]),
        ("grey jumper", "knitwear", ["sweater"]),
        ("black pants for women", "trousers", ["outdoor trousers", "trousers"]),
        # footwear variants
        ("black formal shoes for office", "footwear", None),
        ("comfortable running shoes", "footwear", None),
        ("black ankle boots", "footwear", ["bootie", "boots"]),
        ("ballet flats", "footwear", ["ballerinas", "flat shoe", "flat shoes"]),
        # head noun (right-most) wins
        ("t-shirt dress", "dresses", ["dress"]),
        ("dress shoes", "footwear", None),
        ("hooded jacket", "outerwear", ["jacket"]),
        ("night gown", "nightwear", ["night gown"]),
        # nothing recognised
        ("gaming laptop with RTX graphics", None, None),
        ("clothes suitable for a college student", None, None),
    ],
)
def test_category_and_types(query, category, types):
    assert parse(query) == (category, types)


@pytest.mark.parametrize(
    "query, types",
    [
        # trench coats are typed Coat or Jacket in the catalogue
        ("trench", ["coat", "jacket"]),
        ("trench coat", ["coat", "jacket"]),
        ("beige trench coat", ["coat", "jacket"]),
        ("beige trench coats for women", ["coat", "jacket"]),
        # other coat / jacket queries unchanged
        ("coat", ["coat"]),
        ("overcoat", ["coat"]),
        ("warm winter coat", ["coat"]),
        ("blue coat", ["coat"]),
        ("black jacket", ["jacket"]),
    ],
)
def test_trench_and_coat_vocabulary(query, types):
    assert parse(query) == ("outerwear", types)


def test_raincoat_is_not_parsed_as_coat():
    assert parse("kids raincoat") == (None, None)


def test_word_boundaries_do_not_match_inside_words():
    # "ring" must not fire inside "earring"; "top" not inside "stop" / "laptop".
    assert parse("silver earring")[1] == ["earring", "earrings"]
    assert parse("laptop stand") == (None, None)


@pytest.mark.parametrize(
    "query",
    ["Black casual dress for WOMEN", "red polo shirt for men under $40", "grey jumper"],
)
def test_colour_gender_budget_identical_to_v1(query):
    v1 = QueryParser.extract(query)
    v2 = extract_v2(query)
    for key in ("color", "gender", "budget"):
        assert v2[key] == v1[key]


def test_output_keeps_v1_keys():
    assert {"category", "color", "gender", "budget"} <= set(extract_v2("black dress"))
