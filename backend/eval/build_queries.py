"""
Build the search evaluation set `queries.jsonl` (deterministic).

    python -m eval.build_queries            # from backend/
    python -m eval.build_queries --check    # verify the committed file is up to date

Two parts:
1. Curated queries: the owner's five baseline queries (Q1-Q5), occasion,
   pattern/attribute, kids, synonym, recommendation-intent and
   out-of-catalog cases.
2. Generated queries: "<colour> <type> [for women|men]" combinations that
   the catalog can actually satisfy (>= MIN_AVAILABLE fully relevant items).

Every in-catalog query stores `gain_hist`, the number of catalog items per
achievable relevance gain, so NDCG uses a true ideal ranking. Labels are
derived from catalog attributes (articles.csv) - no product is hand-picked.
Reads articles.csv only; writes only queries.jsonl.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from eval.catalog import DEFAULT_CSV, gain_histogram, load_catalog

OUT = Path(__file__).resolve().parent / "queries.jsonl"
SEED = 20261127
MIN_AVAILABLE = 10
PER_TYPE = 4

JEANS = {"attribute_terms": ["denim", "jeans"], "attribute_appearances": ["Denim"]}
SHOES = ["Shoes"]

# --------------------------------------------------------------------------
# Curated queries
# --------------------------------------------------------------------------
CURATED = [
    # --- Owner's manual baseline (2026-11-27), with v2 acceptance targets ---
    ("b1", "baseline", "black casual dress for women",
     {"product_types": ["Dress"], "related_groups": ["Garment Full body"], "colours": ["Black"], "audience": "women"},
     {"min_results": 5, "type_at5_min": 4, "kids_at5_max": 0}),
    ("b2", "baseline", "summer floral dress",
     {"product_types": ["Dress"], "related_groups": ["Garment Full body"], "audience": "adult",
      "attribute_terms": ["floral", "flower"]},
     {"min_results": 5, "type_at5_min": 4, "kids_at5_max": 0, "attribute_at5_min": 1}),
    ("b3", "baseline", "formal trousers for office wear",
     {"product_types": ["Trousers"], "related_groups": ["Garment Lower body"], "audience": "adult"},
     {"min_results": 5, "type_at5_min": 5}),
    ("b4", "baseline", "comfortable running shoes",
     {"product_types": ["Sneakers", "Other shoe"], "related_groups": SHOES, "audience": "adult",
      "attribute_terms": ["comfort", "soft", "cushion", "running", "sport"]},
     {"min_results": 5, "group_at5_min": 5}),
    ("b5", "baseline", "gaming laptop with RTX graphics",
     {"out_of_catalog": True},
     {"max_results": 0}),

    # --- Occasion / use case (incl. examples from the product brief) ---
    ("o1", "occasion", "black formal shoes for office",
     {"product_types": ["Pumps", "Flat shoe", "Other shoe", "Ballerinas"], "related_groups": SHOES,
      "colours": ["Black"], "audience": "adult"}, {}),
    ("o2", "occasion", "comfortable running shoes for beginners",
     {"product_types": ["Sneakers"], "related_groups": SHOES, "audience": "adult"}, {}),
    ("o3", "occasion", "clothes suitable for a college student",
     {"product_types": ["T-shirt", "Hoodie", "Trousers", "Sneakers", "Bag", "Sweater", "Shirt", "Top"],
      "audience": "adult"}, {}),
    ("o4", "occasion", "party dress for women",
     {"product_types": ["Dress"], "related_groups": ["Garment Full body"], "audience": "women"}, {}),
    ("o5", "occasion", "formal shirt for men for the office",
     {"product_types": ["Shirt"], "related_groups": ["Garment Upper body"], "audience": "men"}, {}),
    ("o6", "occasion", "wedding guest dress",
     {"product_types": ["Dress"], "related_groups": ["Garment Full body"], "audience": "adult"}, {}),
    ("o7", "occasion", "gym leggings for women",
     {"product_types": ["Leggings/Tights"], "related_groups": ["Garment Lower body"], "audience": "women"}, {}),
    ("o8", "occasion", "warm winter coat",
     {"product_types": ["Coat", "Jacket"], "related_groups": ["Garment Upper body"], "audience": "adult"}, {}),
    ("o9", "occasion", "sandals for the beach",
     {"product_types": ["Sandals", "Flip flop", "Heeled sandals"], "related_groups": SHOES, "audience": "adult"}, {}),
    ("o10", "occasion", "office blazer for women",
     {"product_types": ["Blazer"], "related_groups": ["Garment Upper body"], "audience": "women"}, {}),
    ("o11", "occasion", "summer shorts for men",
     {"product_types": ["Shorts"], "related_groups": ["Garment Lower body"], "audience": "men"}, {}),
    ("o12", "occasion", "pyjamas for women",
     {"product_types": ["Pyjama set", "Pyjama bottom", "Night gown", "Pyjama jumpsuit/playsuit"],
      "related_groups": ["Nightwear"], "audience": "women"}, {}),

    # --- Patterns and attributes (soft attribute terms) ---
    ("p1", "attribute", "striped t-shirt",
     {"product_types": ["T-shirt"], "audience": "adult", "attribute_terms": ["stripe"],
      "attribute_appearances": ["Stripe"]}, {}),
    ("p2", "attribute", "denim jacket",
     {"product_types": ["Jacket"], "audience": "adult", **JEANS}, {}),
    ("p3", "attribute", "checked shirt for men",
     {"product_types": ["Shirt"], "audience": "men", "attribute_terms": ["check", "plaid"],
      "attribute_appearances": ["Check"]}, {}),
    ("p4", "attribute", "floral blouse",
     {"product_types": ["Blouse"], "audience": "adult", "attribute_terms": ["floral", "flower"]}, {}),
    ("p5", "attribute", "lace top",
     {"product_types": ["Top", "Blouse", "Vest top", "Bodysuit"], "audience": "adult",
      "attribute_terms": ["lace"]}, {}),
    ("p6", "attribute", "leopard print dress",
     {"product_types": ["Dress"], "audience": "adult", "attribute_terms": ["leopard"]}, {}),
    ("p7", "attribute", "polka dot dress",
     {"product_types": ["Dress"], "audience": "adult", "attribute_terms": ["dot", "spot"],
      "attribute_appearances": ["Dot"]}, {}),
    ("p8", "attribute", "hoodie with a graphic print",
     {"product_types": ["Hoodie"], "audience": "adult", "attribute_terms": ["print"],
      "attribute_appearances": ["Front print", "Placement print"]}, {}),
    ("p9", "attribute", "red knitted sweater for women",
     {"product_types": ["Sweater"], "colours": ["Red"], "audience": "women", "attribute_terms": ["knit"]}, {}),
    ("p10", "attribute", "beige trench coat",
     {"product_types": ["Coat", "Jacket"], "colours": ["Beige"], "audience": "adult",
      "attribute_terms": ["trench"]}, {}),
    ("p11", "attribute", "green linen shirt",
     {"product_types": ["Shirt"], "colours": ["Green"], "audience": "adult", "attribute_terms": ["linen"]}, {}),
    ("p12", "attribute", "black leather boots for women",
     {"product_types": ["Boots"], "related_groups": SHOES, "colours": ["Black"], "audience": "women",
      "attribute_terms": ["leather"]}, {}),
    ("p13", "attribute", "brown leather belt for men",
     {"product_types": ["Belt"], "colours": ["Brown"], "audience": "men", "attribute_terms": ["leather"]}, {}),
    ("p14", "attribute", "pink bikini top",
     {"product_types": ["Bikini top"], "colours": ["Pink"], "audience": "adult"}, {}),

    # --- Kids (children's items ARE the right answer here) ---
    ("k1", "kids", "girls party dress",
     {"product_types": ["Dress"], "related_groups": ["Garment Full body"], "audience": "kids"}, {}),
    ("k2", "kids", "baby bodysuit",
     {"product_types": ["Bodysuit"], "audience": "kids"}, {}),
    ("k3", "kids", "sneakers for boys",
     {"product_types": ["Sneakers"], "related_groups": SHOES, "audience": "kids"}, {}),
    ("k4", "kids", "kids raincoat",
     {"product_types": ["Jacket", "Coat", "Outdoor overall"], "audience": "kids",
      "attribute_terms": ["rain", "water"]}, {}),
    ("k5", "kids", "children's pyjamas",
     {"product_types": ["Pyjama set", "Pyjama jumpsuit/playsuit", "Pyjama bottom"], "audience": "kids"}, {}),
    ("k6", "kids", "winter hat for kids",
     {"product_types": ["Hat/beanie", "Beanie"], "audience": "kids"}, {}),

    # --- Synonyms / vocabulary mismatch ---
    ("s1", "synonym", "black pants for women",
     {"product_types": ["Trousers", "Leggings/Tights"], "colours": ["Black"], "audience": "women"}, {}),
    ("s2", "synonym", "grey jumper",
     {"product_types": ["Sweater"], "colours": ["Grey"], "audience": "adult"}, {}),
    ("s3", "synonym", "white trainers",
     {"product_types": ["Sneakers"], "related_groups": SHOES, "colours": ["White"], "audience": "adult"}, {}),
    ("s4", "synonym", "plain white tee",
     {"product_types": ["T-shirt"], "colours": ["White"], "audience": "adult"}, {}),
    ("s5", "synonym", "navy sweatshirt for men",
     {"product_types": ["Sweater", "Hoodie"], "colours": ["Blue"], "audience": "men"}, {}),
    ("s6", "synonym", "jeans for men",
     {"product_types": ["Trousers"], "audience": "men", **JEANS}, {}),
    ("s7", "synonym", "blue jeans for women",
     {"product_types": ["Trousers"], "colours": ["Blue"], "audience": "women", **JEANS}, {}),
    ("s8", "synonym", "swimming costume",
     {"product_types": ["Swimsuit"], "related_groups": ["Swimwear"], "audience": "adult"}, {}),

    # --- Recommendation intent ("best/recommend/suggest/popular" route) ---
    ("r1", "recommendation", "best black jeans",
     {"product_types": ["Trousers"], "colours": ["Black"], "audience": "adult", **JEANS}, {}),
    ("r2", "recommendation", "recommend a summer dress",
     {"product_types": ["Dress"], "audience": "adult"}, {}),
    ("r3", "recommendation", "suggest white sneakers for men",
     {"product_types": ["Sneakers"], "colours": ["White"], "audience": "men"}, {}),
    ("r4", "recommendation", "popular hoodies",
     {"product_types": ["Hoodie"], "audience": "adult"}, {}),
    ("r5", "recommendation", "best winter jacket for women",
     {"product_types": ["Jacket", "Coat"], "audience": "women"}, {}),
    ("r6", "recommendation", "recommend a black handbag",
     {"product_types": ["Bag"], "colours": ["Black"], "audience": "adult"}, {}),
]

# Products this fashion catalog does not carry. Deliberately excludes things
# it does carry (watches, mobile cases, side tables, cosmetics, dog wear).
OUT_OF_CATALOG = [
    "laptop for programming and machine learning",
    "noise cancelling headphones for travelling",
    "smartphone with 128GB storage",
    "4K smart TV",
    "double door refrigerator",
    "front load washing machine",
    "PS5 game console",
    "DSLR camera for beginners",
    "microwave oven",
    "air fryer",
    "car tyres",
    "android tablet",
    "bluetooth speaker",
    "ergonomic office chair",
    "memory foam mattress",
    "whey protein powder",
    "vitamin D supplements",
    "dry dog food",
    "printer ink cartridge",
    "cordless electric drill",
    "cricket bat",
    "acoustic guitar",
    "three seater sofa",
]

# --------------------------------------------------------------------------
# Generated queries
# --------------------------------------------------------------------------
TYPES = [  # (noun used in the query, acceptable product types)
    ("dress", ["Dress"]), ("trousers", ["Trousers"]), ("sweater", ["Sweater"]),
    ("t-shirt", ["T-shirt"]), ("top", ["Top", "Vest top"]), ("blouse", ["Blouse"]),
    ("jacket", ["Jacket"]), ("shorts", ["Shorts"]), ("shirt", ["Shirt"]),
    ("skirt", ["Skirt"]), ("hoodie", ["Hoodie"]), ("cardigan", ["Cardigan"]),
    ("sneakers", ["Sneakers"]), ("blazer", ["Blazer"]), ("boots", ["Boots"]),
    ("coat", ["Coat"]), ("jumpsuit", ["Jumpsuit/Playsuit"]), ("leggings", ["Leggings/Tights"]),
    ("bag", ["Bag"]), ("sandals", ["Sandals", "Heeled sandals"]), ("swimsuit", ["Swimsuit"]),
    ("bikini top", ["Bikini top"]), ("scarf", ["Scarf"]), ("polo shirt", ["Polo shirt"]),
    ("beanie", ["Hat/beanie", "Beanie"]),
]
COLOURS = ["Black", "White", "Blue", "Pink", "Grey", "Red", "Beige", "Green"]
AUDIENCE_PHRASES = [("women", " for women"), ("men", " for men"), ("adult", "")]


def _primary_group(types, catalog):
    for item in catalog.values():
        if item.product_type == types[0]:
            return item.product_group
    return None


def _full_count(hist, expect):
    top = 1 + sum(1 for k in ("colours", "audience") if expect.get(k))
    return hist.get(f"{top:g}", 0)


def build(catalog) -> list[dict]:
    known_types = {i.product_type for i in catalog.values()}
    known_groups = {i.product_group for i in catalog.values()}
    known_colours = {i.colour for i in catalog.values()}
    rows = []

    for qid, group, query, expect, targets in CURATED:
        row = {"id": qid, "group": group, "query": query, "top_k": 10,
               "expect": expect, "targets": targets}
        if not expect.get("out_of_catalog"):
            for t in expect["product_types"]:
                assert t in known_types, f"{qid}: unknown product type {t!r}"
            for g in expect.get("related_groups", []):
                assert g in known_groups, f"{qid}: unknown product group {g!r}"
            for c in expect.get("colours", []):
                assert c in known_colours, f"{qid}: unknown colour {c!r}"
            row["gain_hist"] = gain_histogram(expect, catalog)
            assert row["gain_hist"], f"{qid}: catalog cannot satisfy this query"
        rows.append(row)

    for n, query in enumerate(OUT_OF_CATALOG, start=1):
        rows.append({"id": f"x{n}", "group": "out_of_catalog", "query": query, "top_k": 10,
                     "expect": {"out_of_catalog": True}, "targets": {"max_results": 0}})

    rng = random.Random(SEED)
    for noun, types in TYPES:
        group = _primary_group(types, catalog)
        combos = [(c, a, p) for c in COLOURS for a, p in AUDIENCE_PHRASES]
        rng.shuffle(combos)
        picked = 0
        for colour, audience, phrase in combos:
            expect = {"product_types": types, "related_groups": [group] if group else [],
                      "colours": [colour], "audience": audience}
            hist = gain_histogram(expect, catalog)
            if _full_count(hist, expect) < MIN_AVAILABLE:
                continue
            picked += 1
            rows.append({"id": f"g{len(rows)}", "group": "generated",
                         "query": f"{colour.lower()} {noun}{phrase}", "top_k": 10,
                         "expect": expect, "targets": {}, "gain_hist": hist})
            if picked >= PER_TYPE:
                break

    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate query ids"
    queries = [r["query"].lower() for r in rows]
    assert len(queries) == len(set(queries)), "duplicate queries"
    return rows


def dumps(rows) -> str:
    return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--csv", default=str(DEFAULT_CSV))
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--check", action="store_true", help="fail if --out is stale")
    args = parser.parse_args(argv)

    text = dumps(build(load_catalog(args.csv)))
    out = Path(args.out)
    if args.check:
        if not out.exists() or out.read_text(encoding="utf-8") != text:
            print(f"{out} is out of date; run python -m eval.build_queries", file=sys.stderr)
            return 1
        print(f"{out} is up to date")
        return 0
    out.write_text(text, encoding="utf-8")
    print(f"wrote {text.count(chr(10))} queries to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
