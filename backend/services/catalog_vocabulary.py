"""Catalogue vocabulary for search v2 (Phase 1, S1).

Plain data only. Used by ``query_parser_v2`` and ``semantic_reranker_v2``;
the v1 parser and reranker do not import this module.

Every key in ``PRODUCT_TYPE_CATEGORY`` is a real ``product_type_name`` value
from the H&M catalogue (all 131 of them, lower-cased). ``tests/
test_catalog_vocabulary.py`` checks this against ``articles.csv``.

Category names already used by v1 (tops, trousers, outerwear, knitwear,
footwear, bags, swimwear, nightwear) are kept, so session-intent categories
stay compatible.
"""

# ---------------------------------------------------------------------------
# Product type -> category (product side). Looked up before anything else;
# section / department / garment-group text is never used to override it.
# ---------------------------------------------------------------------------

_CATEGORY_TYPES = {
    "tops": [
        "T-shirt", "Top", "Blouse", "Shirt", "Vest top", "Bodysuit", "Polo shirt",
    ],
    "hoodies": ["Hoodie"],
    "knitwear": ["Sweater", "Cardigan"],
    "outerwear": [
        "Jacket", "Blazer", "Coat", "Outdoor Waistcoat", "Tailored Waistcoat",
        "Outdoor overall",
    ],
    "trousers": ["Trousers", "Shorts", "Leggings/Tights", "Outdoor trousers"],
    "skirts": ["Skirt"],
    "dresses": ["Dress"],
    "jumpsuits": ["Jumpsuit/Playsuit", "Dungarees"],
    "sets": ["Garment Set", "Costumes"],
    "swimwear": [
        "Swimwear bottom", "Bikini top", "Swimsuit", "Swimwear set", "Sarong",
        "Swimwear top",
    ],
    "nightwear": [
        "Pyjama set", "Pyjama jumpsuit/playsuit", "Pyjama bottom", "Night gown",
        "Robe", "Sleeping sack", "Sleep Bag",
    ],
    "underwear": [
        "Underwear bottom", "Bra", "Underwear body", "Kids Underwear top",
        "Underwear set", "Long John", "Underdress", "Nipple covers",
        "Underwear corset", "Bra extender",
    ],
    "socks_tights": ["Socks", "Underwear Tights", "Leg warmers"],
    "footwear": [
        "Sneakers", "Boots", "Sandals", "Other shoe", "Ballerinas", "Slippers",
        "Heeled sandals", "Pumps", "Flat shoe", "Flip flop", "Wedge", "Bootie",
        "Heels", "Flat shoes", "Moccasins", "Pre-walkers",
    ],
    "bags": [
        "Bag", "Weekend/Gym bag", "Backpack", "Cross-body bag", "Tote bag",
        "Shoulder bag", "Bumbag",
    ],
    "accessories": [
        "Hat/beanie", "Earring", "Other accessories", "Scarf", "Hair/alice band",
        "Sunglasses", "Necklace", "Cap/peaked", "Belt", "Hat/brim", "Gloves",
        "Hair clip", "Ring", "Hair string", "Bracelet", "Tie", "Wallet", "Watch",
        "Beanie", "Umbrella", "Hair ties", "Cap", "Earrings", "Felt hat",
        "Bucket hat", "Accessories set", "Alice band", "Straw hat", "Braces",
        "Hairband", "Eyeglasses", "Headband", "Mobile case",
        "Wireless earphone case", "Keychain",
    ],
    "other": [
        "Soft Toys", "Waterbottle", "Dog Wear", "Dog wear", "Giftbox", "Baby Bib",
        "Fine cosmetics", "Chem. cosmetics", "Side table", "Zipper head",
        "Stain remover spray", "Washing bag", "Sewing kit", "Wood balls",
        "Clothing mist", "Marker pen", "Blanket", "Cushion", "Towel", "Toy",
    ],
}


def normalise(value) -> str:
    """Lower-case, trim and collapse whitespace."""
    return " ".join(str(value or "").lower().split())


PRODUCT_TYPE_CATEGORY = {
    normalise(t): category
    for category, types in _CATEGORY_TYPES.items()
    for t in types
}

# Fallback when a product's type is missing or not in the table:
# its product group (stored as ``category`` in catalog_products).
PRODUCT_GROUP_CATEGORY = {
    "swimwear": "swimwear",
    "shoes": "footwear",
    "bags": "bags",
    "nightwear": "nightwear",
    "underwear": "underwear",
    "underwear/nightwear": "nightwear",
    "socks & tights": "socks_tights",
    "accessories": "accessories",
    "items": "accessories",
}

# ---------------------------------------------------------------------------
# Query side: phrase -> (category, specific product types or None).
#
# A phrase that names catalogue types is "specific": products of those types
# rank first, then the rest of the broad category backfills. A phrase with
# ``None`` only sets the broad category (the v1 behaviour).
#
# The parser picks the longest phrase, and among non-overlapping matches the
# right-most one (the head noun: "polo shirt", "t-shirt dress", "dress shoes").
# Plurals "-s" / "-es" are matched automatically.
# ---------------------------------------------------------------------------

_HATS = ["Hat/beanie", "Hat/brim", "Beanie", "Felt hat", "Bucket hat", "Straw hat"]
_JEWELLERY = ["Earring", "Earrings", "Necklace", "Ring", "Bracelet"]

_QUERY_TERMS = [
    # swimwear
    (["bikini top"], "swimwear", ["Bikini top"]),
    (["bikini bottom", "swim shorts", "swim trunks", "swimming trunks"],
     "swimwear", ["Swimwear bottom"]),
    (["bikini"], "swimwear", ["Bikini top", "Swimwear bottom", "Swimwear set"]),
    (["swimsuit", "swim suit", "swimming costume", "bathing suit", "one-piece"],
     "swimwear", ["Swimsuit"]),
    (["sarong"], "swimwear", ["Sarong"]),
    (["swimwear", "beachwear", "tankini"], "swimwear", None),
    # tops
    (["polo shirt", "polo"], "tops", ["Polo shirt"]),
    (["t-shirt", "tshirt", "t shirt", "tee"], "tops", ["T-shirt"]),
    (["vest top", "tank top", "tank", "camisole", "cami"], "tops", ["Vest top"]),
    (["blouse"], "tops", ["Blouse"]),
    (["bodysuit"], "tops", ["Bodysuit"]),
    (["shirt"], "tops", ["Shirt"]),
    (["top"], "tops", None),
    # hoodies / knitwear
    (["hoodie", "hoody"], "hoodies", ["Hoodie"]),
    (["sweater", "jumper", "pullover", "sweatshirt"], "knitwear", ["Sweater"]),
    (["cardigan"], "knitwear", ["Cardigan"]),
    (["knitwear"], "knitwear", None),
    # outerwear
    (["jacket", "bomber", "puffer", "windbreaker", "anorak"], "outerwear", ["Jacket"]),
    (["coat", "overcoat"], "outerwear", ["Coat"]),
    # The catalogue types most trench coats as Jacket (75 vs 49 Coat).
    (["trench", "trench coat"], "outerwear", ["Coat", "Jacket"]),
    (["parka"], "outerwear", ["Jacket", "Coat"]),
    (["blazer"], "outerwear", ["Blazer"]),
    (["waistcoat", "gilet"], "outerwear", ["Outdoor Waistcoat", "Tailored Waistcoat"]),
    (["outerwear"], "outerwear", None),
    # lower body
    (["leggings"], "trousers", ["Leggings/Tights"]),
    (["tights"], "socks_tights", ["Underwear Tights", "Leggings/Tights"]),
    (["shorts"], "trousers", ["Shorts"]),
    (["trousers", "pants", "chinos", "slacks", "joggers", "jeans"],
     "trousers", ["Trousers", "Outdoor trousers"]),
    (["skirt"], "skirts", ["Skirt"]),
    # full body
    (["dress", "gown", "sundress", "shirt dress", "t-shirt dress", "sweater dress"],
     "dresses", ["Dress"]),
    (["jumpsuit", "playsuit", "romper"], "jumpsuits", ["Jumpsuit/Playsuit"]),
    (["dungarees"], "jumpsuits", ["Dungarees"]),
    # nightwear / underwear / socks
    (["night gown", "nightgown", "nightdress", "nightie"], "nightwear", ["Night gown"]),
    (["robe", "bathrobe", "dressing gown"], "nightwear", ["Robe"]),
    (["pyjamas", "pajamas", "pyjama", "pajama", "pjs", "sleepwear", "nightwear"],
     "nightwear", None),
    (["bra"], "underwear", ["Bra"]),
    (["briefs", "boxers", "knickers", "panties"], "underwear", ["Underwear bottom"]),
    (["underwear", "lingerie"], "underwear", None),
    (["socks"], "socks_tights", ["Socks"]),
    # footwear
    (["sneakers", "sneaker", "trainers", "trainer"], "footwear", ["Sneakers"]),
    (["boots", "boot", "ankle boots"], "footwear", ["Boots", "Bootie"]),
    (["sandals", "sandal"], "footwear", ["Sandals", "Heeled sandals"]),
    (["heels", "high heels", "pumps", "stilettos"],
     "footwear", ["Heels", "Pumps", "Heeled sandals", "Wedge"]),
    (["wedges"], "footwear", ["Wedge"]),
    (["flip flops", "flip-flops", "flip flop"], "footwear", ["Flip flop"]),
    (["slippers"], "footwear", ["Slippers"]),
    (["ballerinas", "ballet flats", "flats"],
     "footwear", ["Ballerinas", "Flat shoe", "Flat shoes"]),
    (["loafers", "moccasins"], "footwear", ["Moccasins", "Other shoe", "Flat shoe"]),
    (["shoes", "shoe", "footwear"], "footwear", None),
    # bags
    (["backpack", "rucksack"], "bags", ["Backpack"]),
    (["gym bag", "weekend bag"], "bags", ["Weekend/Gym bag"]),
    (["bag", "handbag", "tote", "purse", "clutch", "shoulder bag", "crossbody"],
     "bags", None),
    # accessories
    (["scarf", "scarves"], "accessories", ["Scarf"]),
    (["beanie"], "accessories", ["Hat/beanie", "Beanie"]),
    (["bucket hat"], "accessories", ["Bucket hat", "Hat/brim"]),
    (["hat"], "accessories", _HATS),
    (["cap", "baseball cap"], "accessories", ["Cap/peaked", "Cap"]),
    (["belt"], "accessories", ["Belt"]),
    (["sunglasses"], "accessories", ["Sunglasses"]),
    (["gloves", "mittens"], "accessories", ["Gloves"]),
    (["earrings", "earring"], "accessories", ["Earring", "Earrings"]),
    (["necklace"], "accessories", ["Necklace"]),
    (["bracelet"], "accessories", ["Bracelet"]),
    (["ring"], "accessories", ["Ring"]),
    (["jewellery", "jewelry"], "accessories", _JEWELLERY),
    (["watch"], "accessories", ["Watch"]),
    (["tie"], "accessories", ["Tie"]),
    (["wallet"], "accessories", ["Wallet"]),
    (["umbrella"], "accessories", ["Umbrella"]),
    (["hair clip", "hair band", "headband", "alice band", "hair tie"],
     "accessories", ["Hair clip", "Hair/alice band", "Hairband", "Headband",
                     "Alice band", "Hair ties", "Hair string"]),
    (["accessories", "accessory"], "accessories", None),
]

# phrase -> (category, frozenset of normalised product types or None)
QUERY_TERMS = {
    normalise(phrase): (
        category,
        frozenset(normalise(t) for t in types) if types else None,
    )
    for phrases, category, types in _QUERY_TERMS
    for phrase in phrases
}

CATEGORIES = frozenset(_CATEGORY_TYPES)

# ---------------------------------------------------------------------------
# Audience (S4). Children's products are identified by ``section``: these 13
# sections hold exactly the catalogue's 34,711 "Baby/Children" articles and no
# section mixes children's and adult products (checked against articles.csv
# in tests/test_kids_downrank.py).
# ---------------------------------------------------------------------------

KIDS_SECTIONS = frozenset(
    normalise(s)
    for s in [
        "Baby Boy", "Baby Essentials & Complements", "Baby Girl",
        "Boys Underwear & Basics", "Girls Underwear & Basics", "Kids & Baby Shoes",
        "Kids Accessories, Swimwear & D", "Kids Boy", "Kids Girl",
        "Kids Local Relevance", "Kids Outerwear", "Young Boy", "Young Girl",
    ]
)

# A query containing any of these allows children's products (no penalty).
KIDS_QUERY_TERMS = [
    "kid", "kids", "kid's", "child", "children", "children's", "childrens",
    "baby", "babies", "toddler", "toddlers", "infant", "infants", "newborn",
    "newborns", "girl", "girls", "boy", "boys", "junior", "juniors",
]

# Audience unclear: also no penalty (keep v2 behaviour).
AMBIGUOUS_AUDIENCE_TERMS = [
    "teen", "teens", "teenager", "teenagers", "school", "daughter", "daughters",
    "son", "sons", "family", "matching",
]

# Adult phrases that contain a kids word; removed before the checks above.
ADULT_PHRASES = [
    "baby pink", "baby blue", "girls' night", "girls night", "girl's night",
    "babydoll", "baby-doll", "baby doll",
]
