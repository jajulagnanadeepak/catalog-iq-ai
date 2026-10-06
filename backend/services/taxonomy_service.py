"""
Catalog taxonomy mapping for CatalogIQ AI.

Maps application-level user intent categories to
H&M catalog terminology.
"""

CATEGORY_KEYWORDS = {
    "outerwear": {
        "coat",
        "coats",
        "jacket",
        "jackets",
        "blazer",
        "blazers",
        "parka",
        "parkas",
        "overcoat",
        "overcoats",
        "trench",
        "trenchcoat",
        "puffer",
        "windbreaker",
        "anorak",
        "bomber",
        "cardigan",
    },

    "tops": {
        "top",
        "tops",
        "shirt",
        "shirts",
        "blouse",
        "blouses",
        "t-shirt",
        "tshirt",
        "tee",
        "vest top",
        "tank",
        "tank top",
        "crop top",
        "camisole",
        "cami",
        "bodysuit",
        "polo",
    },

    "trousers": {
        "trouser",
        "trousers",
        "pants",
        "jeans",
        "legging",
        "leggings",
        "shorts",
        "chinos",
        "joggers",
    },

    "footwear": {
        "shoe",
        "shoes",
        "sneaker",
        "sneakers",
        "boot",
        "boots",
        "sandal",
        "sandals",
        "heel",
        "heels",
        "loafer",
        "loafers",
        "slipper",
        "slippers",
    },

    "bags": {
        "bag",
        "bags",
        "backpack",
        "backpacks",
        "handbag",
        "handbags",
        "shoulder bag",
        "tote",
        "purse",
        "clutch",
    },

    "swimwear": {
        "swimwear",
        "swimsuit",
        "swimsuits",
        "bikini",
        "bikinis",
        "bikini top",
        "tankini",
        "swim",
        "beachwear",
    },

    "knitwear": {
        "knitwear",
        "knit",
        "knitted",
        "sweater",
        "sweaters",
        "jumper",
        "jumpers",
        "pullover",
        "pullovers",
        "cardigan",
        "cardigans",
    },
}


class TaxonomyService:

    @staticmethod
    def normalize_category(
        category: str | None,
    ) -> str | None:

        if not category:
            return None

        category = category.lower().strip()

        aliases = {
            "outerwear": "outerwear",
            "outer wear": "outerwear",
            "outwear": "outerwear",

            "tops": "tops",
            "top": "tops",

            "trousers": "trousers",
            "trouser": "trousers",
            "pants": "trousers",

            "footwear": "footwear",
            "shoes": "footwear",
            "shoe": "footwear",

            "bags": "bags",
            "bag": "bags",

            "swimwear": "swimwear",
            "swim": "swimwear",

            "knitwear": "knitwear",
            "knit": "knitwear",
        }

        return aliases.get(
            category,
            category,
        )

    @classmethod
    def product_matches_category(
        cls,
        product: dict,
        category: str | None,
    ) -> bool:

        normalized = cls.normalize_category(
            category
        )

        if not normalized:
            return False

        keywords = CATEGORY_KEYWORDS.get(
            normalized,
            set(),
        )

        if not keywords:
            return False

        searchable_text = " ".join(
            [
                str(product.get("name", "")),
                str(product.get("product_type", "")),
                str(product.get("category", "")),
                str(product.get("department", "")),
                str(product.get("section", "")),
                str(product.get("garment_group", "")),
                str(product.get("description", "")),
            ]
        ).lower()

        for keyword in keywords:

            if keyword in searchable_text:
                return True

        return False

    @classmethod
    def category_match_score(
        cls,
        product: dict,
        category: str | None,
    ) -> float:

        normalized = cls.normalize_category(
            category
        )

        if not normalized:
            return 0.0

        keywords = CATEGORY_KEYWORDS.get(
            normalized,
            set(),
        )

        if not keywords:
            return 0.0

        fields = {
            "name": str(
                product.get("name", "")
            ),
            "product_type": str(
                product.get("product_type", "")
            ),
            "category": str(
                product.get("category", "")
            ),
            "department": str(
                product.get("department", "")
            ),
            "section": str(
                product.get("section", "")
            ),
            "garment_group": str(
                product.get("garment_group", "")
            ),
            "description": str(
                product.get("description", "")
            ),
        }

        weighted_fields = [
            (fields["name"], 0.40),
            (fields["product_type"], 0.30),
            (fields["category"], 0.10),
            (fields["department"], 0.05),
            (fields["section"], 0.05),
            (fields["garment_group"], 0.05),
            (fields["description"], 0.05),
        ]

        score = 0.0

        for text, weight in weighted_fields:

            text = text.lower()

            if any(
                keyword in text
                for keyword in keywords
            ):
                score += weight

        return round(
            min(score, 1.0),
            4,
        )


taxonomy_service = TaxonomyService()