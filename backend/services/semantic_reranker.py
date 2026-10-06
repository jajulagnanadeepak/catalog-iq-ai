import re
from collections import defaultdict

from services.taxonomy_service import taxonomy_service
from services.query_parser import query_parser


class SemanticReranker:

    def __init__(self):
        self.weights = {
            "semantic": 0.40,
            "keyword": 0.15,
            "attributes": 0.35,
            "intent": 0.10,
        }

        self.stop_words = {
            "for",
            "the",
            "a",
            "an",
            "with",
            "and",
            "of",
            "in",
            "on",
            "to",
            "is",
            "are",
            "me",
            "my",
        }

    # =========================================================
    # MAIN RERANKING
    # =========================================================

    def rerank(
        self,
        query,
        results,
        limit=10,
        max_category_ratio=0.35,
        session_intent=None,
    ):

        if not results:
            return []

        query_tokens = self._tokenize(query)

        # Extract category, color, gender, budget, etc.
        attributes = query_parser.extract(query)

        scored = []

        for item in results:

            product = item.get("product", {})

            distance = float(
                item.get("distance", 0.0)
            )

            # -------------------------------------------------
            # HARD CATEGORY FILTER
            # -------------------------------------------------

            query_category = attributes.get("category")

            if query_category:

                product_category = (
                    self._infer_product_category(product)
                )

                if product_category != query_category:
                    continue

            # -------------------------------------------------
            # SCORES
            # -------------------------------------------------

            semantic_score = self._semantic_score(
                distance
            )

            keyword_score = self._keyword_score(
                query_tokens,
                product,
            )

            attribute_score = self._attribute_score(
                product,
                attributes,
            )

            intent_score = self._product_intent_score(
                product,
                session_intent,
            )

            # -------------------------------------------------
            # FINAL SCORE
            # -------------------------------------------------

            final_score = (
                self.weights["semantic"]
                * semantic_score
                + self.weights["keyword"]
                * keyword_score
                + self.weights["attributes"]
                * attribute_score
                + self.weights["intent"]
                * intent_score
            )

            scored.append(
                {
                    **item,
                    "_semantic_score": semantic_score,
                    "_keyword_score": keyword_score,
                    "_attribute_score": attribute_score,
                    "_intent_score": intent_score,
                    "_final_score": final_score,
                }
            )

        # -----------------------------------------------------
        # SORT
        # -----------------------------------------------------

        scored.sort(
            key=lambda x: x["_final_score"],
            reverse=True,
        )

        # -----------------------------------------------------
        # DEDUPLICATION
        # -----------------------------------------------------

        deduplicated = self._apply_deduplication(
            scored
        )

        # -----------------------------------------------------
        # CATEGORY / DIVERSITY
        # -----------------------------------------------------

        # If the user explicitly requested a category,
        # returning 10 products from that category is correct.
        #
        # Example:
        # "black top for women"
        # -> return tops
        #
        # "black jeans for women"
        # -> return trousers/jeans

        if attributes.get("category"):

            selected = deduplicated[:limit]

        else:

            selected = self._apply_diversity(
                deduplicated,
                limit,
                max_category_ratio,
            )

        # Final safety sort
        selected.sort(
            key=lambda x: x["_final_score"],
            reverse=True,
        )

        # -----------------------------------------------------
        # RESPONSE
        # -----------------------------------------------------

        recommendations = []

        for rank, item in enumerate(
            selected,
            start=1,
        ):

            product = item["product"]

            recommendations.append(
                {
                    "rank": rank,
                    "article_id": item["article_id"],
                    "score": round(
                        item["_final_score"],
                        4,
                    ),
                    "semantic_score": round(
                        item["_semantic_score"],
                        4,
                    ),
                    "keyword_score": round(
                        item["_keyword_score"],
                        4,
                    ),
                    "attribute_score": round(
                        item["_attribute_score"],
                        4,
                    ),
                    "intent_score": round(
                        item["_intent_score"],
                        4,
                    ),
                    "distance": round(
                        float(item["distance"]),
                        4,
                    ),
                    "reason": self._build_reason(
                        query=query,
                        product=product,
                        attributes=attributes,
                        session_intent=session_intent,
                    ),
                    "product": product,
                }
            )

        return recommendations

    # =========================================================
    # DEDUPLICATION
    # =========================================================

    def _apply_deduplication(self, scored):

        """
        Different article IDs can represent the same
        product/style.

        Example:

        Madison skinny HW
        Madison skinny HW
        Madison skinny HW

        Keep only the highest-scoring variant.
        """

        seen = set()
        selected = []

        for item in scored:

            product = item.get(
                "product",
                {},
            )

            name = str(
                product.get(
                    "name",
                    "",
                )
            ).strip().lower()

            product_type = str(
                product.get(
                    "product_type",
                    "",
                )
            ).strip().lower()

            if not name:

                selected.append(item)
                continue

            # Normalize whitespace
            name = " ".join(
                name.split()
            )

            product_type = " ".join(
                product_type.split()
            )

            # Same style + same product type
            style_key = (
                name,
                product_type,
            )

            if style_key in seen:
                continue

            seen.add(style_key)

            selected.append(item)

        return selected

    # =========================================================
    # SEMANTIC SCORE
    # =========================================================

    @staticmethod
    def _semantic_score(distance):

        return 1.0 / (
            1.0 + max(
                distance,
                0.0,
            )
        )

    # =========================================================
    # KEYWORD SCORE
    # =========================================================

    def _keyword_score(
        self,
        query_tokens,
        product,
    ):

        if not query_tokens:
            return 0.0

        searchable_text = " ".join(
            [
                str(
                    product.get(
                        "name",
                        "",
                    )
                ),
                str(
                    product.get(
                        "product_type",
                        "",
                    )
                ),
                str(
                    product.get(
                        "category",
                        "",
                    )
                ),
                str(
                    product.get(
                        "department",
                        "",
                    )
                ),
                str(
                    product.get(
                        "section",
                        "",
                    )
                ),
                str(
                    product.get(
                        "garment_group",
                        "",
                    )
                ),
                str(
                    product.get(
                        "colour",
                        "",
                    )
                ),
                str(
                    product.get(
                        "description",
                        "",
                    )
                ),
            ]
        )

        product_tokens = self._tokenize(
            searchable_text
        )

        if not product_tokens:
            return 0.0

        matches = query_tokens.intersection(
            product_tokens
        )

        return len(matches) / len(
            query_tokens
        )

    # =========================================================
    # ATTRIBUTE SCORE
    # =========================================================

    def _attribute_score(
        self,
        product,
        attributes,
    ):

        requested = 0
        matched = 0.0

        # -----------------------------------------------------
        # CATEGORY
        # -----------------------------------------------------

        query_category = attributes.get(
            "category"
        )

        if query_category:

            requested += 1

            product_category = (
                self._infer_product_category(
                    product
                )
            )

            if product_category == query_category:
                matched += 1

        # -----------------------------------------------------
        # COLOR
        # -----------------------------------------------------

        query_color = attributes.get(
            "color"
        )

        if query_color:

            requested += 1

            product_color = str(
                product.get(
                    "colour",
                    "",
                )
            ).lower().strip()

            if query_color in product_color:
                matched += 1

        # -----------------------------------------------------
        # GENDER
        # -----------------------------------------------------

        query_gender = attributes.get(
            "gender"
        )

        if query_gender:

            requested += 1

            product_gender = (
                self._infer_gender(
                    product
                )
            )

            if product_gender == query_gender:

                matched += 1

            elif product_gender == "unisex":

                matched += 0.5

        # -----------------------------------------------------
        # BUDGET
        # -----------------------------------------------------

        # Current H&M catalog does not contain
        # a reliable price field.
        #
        # Therefore budget is intentionally
        # not scored here.

        if requested == 0:
            return 0.0

        return matched / requested

    # =========================================================
    # PRODUCT CATEGORY
    # =========================================================

    def _infer_product_category(
        self,
        product,
    ):

        product_type = str(
            product.get(
                "product_type",
                "",
            )
        ).lower().strip()

        category = str(
            product.get(
                "category",
                "",
            )
        ).lower().strip()

        department = str(
            product.get(
                "department",
                "",
            )
        ).lower().strip()

        section = str(
            product.get(
                "section",
                "",
            )
        ).lower().strip()

        garment_group = str(
            product.get(
                "garment_group",
                "",
            )
        ).lower().strip()

        # -----------------------------------------------------
        # SWIMWEAR
        # -----------------------------------------------------

        if (
            category == "swimwear"
            or department == "swimwear"
            or garment_group == "swimwear"
            or "swimwear" in section
            or "beachwear" in section
        ):

            return "swimwear"

        # -----------------------------------------------------
        # NIGHTWEAR
        # -----------------------------------------------------

        if (
            "nightwear" in category
            or "nightwear" in garment_group
            or "nightwear" in section
            or "night wear" in section
        ):

            return "nightwear"

        # -----------------------------------------------------
        # FOOTWEAR
        # -----------------------------------------------------

        footwear_types = {
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
        }

        if product_type in footwear_types:
            return "footwear"

        # -----------------------------------------------------
        # BAGS
        # -----------------------------------------------------

        bag_types = {
            "bag",
            "bags",
            "backpack",
            "backpacks",
            "handbag",
            "handbags",
            "tote",
            "purse",
            "clutch",
        }

        if product_type in bag_types:
            return "bags"

        # -----------------------------------------------------
        # OUTERWEAR
        # -----------------------------------------------------

        outerwear_types = {
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
            "trenchcoat",
            "trench coat",
            "puffer",
            "windbreaker",
            "anorak",
            "bomber",
        }

        if product_type in outerwear_types:
            return "outerwear"

        # -----------------------------------------------------
        # TROUSERS
        # -----------------------------------------------------

        trouser_types = {
            "trouser",
            "trousers",
            "pants",
            "jeans",
            "legging",
            "leggings",
            "shorts",
            "chinos",
            "joggers",
        }

        if product_type in trouser_types:
            return "trousers"

        # -----------------------------------------------------
        # KNITWEAR
        # -----------------------------------------------------

        knitwear_types = {
            "knitwear",
            "sweater",
            "sweaters",
            "jumper",
            "jumpers",
            "pullover",
            "pullovers",
            "cardigan",
            "cardigans",
        }

        if product_type in knitwear_types:
            return "knitwear"

        # -----------------------------------------------------
        # TOPS
        # -----------------------------------------------------

        top_types = {
            "top",
            "vest top",
            "shirt",
            "shirts",
            "blouse",
            "blouses",
            "t-shirt",
            "tshirt",
            "tee",
            "tank top",
            "camisole",
            "cami",
            "bodysuit",
            "polo",
        }

        if product_type in top_types:
            return "tops"

        # -----------------------------------------------------
        # FALLBACK
        # -----------------------------------------------------

        return None

    # =========================================================
    # PRODUCT GENDER
    # =========================================================

    @staticmethod
    def _infer_gender(
        product,
    ):

        text = " ".join(
            [
                str(
                    product.get(
                        "department",
                        "",
                    )
                ),
                str(
                    product.get(
                        "section",
                        "",
                    )
                ),
                str(
                    product.get(
                        "category",
                        "",
                    )
                ),
                str(
                    product.get(
                        "description",
                        "",
                    )
                ),
            ]
        ).lower()

        # Women
        if any(
            word in text
            for word in [
                "women",
                "womens",
                "ladies",
                "lady",
            ]
        ):

            return "women"

        # Men
        if any(
            word in text
            for word in [
                "men",
                "mens",
                "male",
            ]
        ):

            return "men"

        return None

    # =========================================================
    # SESSION INTENT
    # =========================================================

    def _product_intent_score(
        self,
        product,
        session_intent,
    ):

        if not session_intent:
            return 0.0

        primary_category = (
            session_intent.get(
                "primary_category"
            )
        )

        if not primary_category:
            return 0.0

        return taxonomy_service.category_match_score(
            product=product,
            category=primary_category,
        )

    # =========================================================
    # DIVERSITY
    # =========================================================

    def _apply_diversity(
        self,
        scored,
        limit,
        max_category_ratio,
    ):

        max_per_category = max(
            1,
            int(
                limit
                * max_category_ratio
            ),
        )

        category_counts = defaultdict(int)

        selected = []

        for item in scored:

            product = item["product"]

            category = (
                self._infer_product_category(
                    product
                )
                or "unknown"
            )

            if (
                category_counts[category]
                >= max_per_category
            ):
                continue

            selected.append(item)

            category_counts[category] += 1

            if len(selected) >= limit:
                break

        return selected[:limit]

    # =========================================================
    # TOKENIZER
    # =========================================================

    def _tokenize(
        self,
        text,
    ):

        if not text:
            return set()

        tokens = set(
            re.findall(
                r"[a-z0-9]+",
                text.lower(),
            )
        )

        return {
            token
            for token in tokens
            if token not in self.stop_words
        }

    # =========================================================
    # EXPLANATION
    # =========================================================

    def _build_reason(
        self,
        query,
        product,
        attributes,
        session_intent,
    ):

        name = product.get(
            "name",
            "This product",
        )

        reasons = []

        # -----------------------------------------------------
        # CATEGORY
        # -----------------------------------------------------

        category = attributes.get(
            "category"
        )

        if category:

            product_category = (
                self._infer_product_category(
                    product
                )
            )

            if product_category == category:

                reasons.append(
                    f"matches your {category} request"
                )

        # -----------------------------------------------------
        # COLOR
        # -----------------------------------------------------

        color = attributes.get(
            "color"
        )

        if color:

            product_color = str(
                product.get(
                    "colour",
                    "",
                )
            ).lower()

            if color in product_color:

                reasons.append(
                    f"matches the {color} color"
                )

        # -----------------------------------------------------
        # GENDER
        # -----------------------------------------------------

        gender = attributes.get(
            "gender"
        )

        if gender:

            product_gender = (
                self._infer_gender(
                    product
                )
            )

            if product_gender == gender:

                reasons.append(
                    f"matches your {gender} preference"
                )

        # -----------------------------------------------------
        # BUILD EXPLANATION
        # -----------------------------------------------------

        if reasons:

            return (
                f"{name} "
                + " and ".join(reasons)
                + "."
            )

        # -----------------------------------------------------
        # SESSION INTENT FALLBACK
        # -----------------------------------------------------

        if session_intent:

            session_category = (
                session_intent.get(
                    "primary_category"
                )
            )

            if session_category:

                return (
                    f"{name} is relevant to your search "
                    f"and recent interest in "
                    f"{session_category}."
                )

        # -----------------------------------------------------
        # DEFAULT
        # -----------------------------------------------------

        return (
            f"{name} is semantically relevant "
            f"to '{query}'."
        )


# =============================================================
# SINGLE RERANKER INSTANCE
# =============================================================

reranker = SemanticReranker()