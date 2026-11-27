"""Search reranker v2 (Phase 1, S1 + S2). Selected with SEARCH_RERANK_VERSION=v2.

Subclasses the v1 ``SemanticReranker`` and reuses every scoring helper and
the final-score formula unchanged. Differences from v1:

S1 - category vocabulary and specificity
  * ``_infer_product_category`` maps all 131 catalogue product types
    (``services.catalog_vocabulary``), falling back to the product group.
    Section / department text never overrides the product type.
  * Queries are parsed with ``query_parser_v2`` (longest phrase / head noun).
  * When the query names specific product types ("polo shirt", "leggings",
    "bikini top"), products of those types rank first; the rest of the broad
    category backfills the remaining slots. Products outside the category are
    never used for backfill.

S2 - diversity cap with backfill (queries without a category)
  * Cap per category is ``max(2, int(limit * ratio))``.
  * If the capped pass returns fewer than ``limit``, the remaining slots are
    filled from the skipped candidates in score order.

S4 - children's-product downranking (only with ``kids_penalty > 0``,
  i.e. SEARCH_V2_KIDS_DOWNRANK=true)
  * For queries that don't allow children's products (``allows_kids``),
    ``KIDS_PENALTY`` is subtracted from a children's product's final score
    before the selection above. Nothing is removed; the returned ``score`` is
    the ranking score, so it includes the penalty.

S3-lite - explicit attributes (only with ``attribute_boost=True``,
  i.e. SEARCH_V2_ATTRIBUTE_BOOST=true)
  * If the query names a pattern (``extract_patterns``) and S1 detects a
    category, ``PATTERN_BOOST`` x (share of requested patterns found in the
    product's name/description) is added to the final score. Non-matching
    products get nothing; there is no penalty.
  * Colour synonym navy -> dark blue in the colour check.

Ordering is deterministic: score descending, ties broken by FAISS rank.
The response items have exactly the v1 shape.
"""

from collections import defaultdict

from services.catalog_vocabulary import (
    COLOUR_SYNONYMS,
    KIDS_SECTIONS,
    PATTERN_BOOST,
    PRODUCT_GROUP_CATEGORY,
    PRODUCT_TYPE_CATEGORY,
    normalise,
)
from services.query_parser_v2 import (
    PRODUCT_PATTERN_REGEXES,
    allows_kids,
    extract_patterns,
    extract_v2,
)
from services.semantic_reranker import SemanticReranker

RERANK_VERSION = "v2"

# S4: soft penalty subtracted from a children's product's final score when the
# query does not allow children's products. Enabled by SEARCH_V2_KIDS_DOWNRANK.
KIDS_PENALTY = 0.10


def _sort_key(item):
    return (-item["_final_score"], item["_position"])


class SemanticRerankerV2(SemanticReranker):

    version = RERANK_VERSION

    def __init__(self, kids_penalty: float = 0.0, attribute_boost: bool = False):
        super().__init__()
        # 0.0 = S1 + S2 only (identical to v2 before S4).
        self.kids_penalty = float(kids_penalty)
        # False = no S3-lite (no pattern boost, no colour synonym).
        self.attribute_boost = bool(attribute_boost)

    # ---------------------------------------------------------
    # S3-lite: pattern boost and colour synonym
    # ---------------------------------------------------------

    @staticmethod
    def _pattern_match_fraction(product, requirements):
        """Share of requested patterns found in the product's name or
        description. Missing text matches nothing (no boost, no penalty)."""
        text = " ".join(
            str(product.get(field) or "") for field in ("name", "description")
        ).lower()
        matched = sum(
            any(PRODUCT_PATTERN_REGEXES[key].search(text) for key in keys)
            for keys in requirements
        )
        return matched / len(requirements)

    def _attribute_score(self, product, attributes):
        colour = attributes.get("color")
        if self.attribute_boost and colour in COLOUR_SYNONYMS:
            attributes = {**attributes, "color": COLOUR_SYNONYMS[colour]}
        return super()._attribute_score(product, attributes)

    # ---------------------------------------------------------
    # S4: children's products
    # ---------------------------------------------------------

    @staticmethod
    def _is_kids_product(product):
        return normalise(product.get("section")) in KIDS_SECTIONS

    # ---------------------------------------------------------
    # S1: product category from the catalogue vocabulary
    # ---------------------------------------------------------

    def _infer_product_category(self, product):
        product_type = normalise(product.get("product_type"))
        category = PRODUCT_TYPE_CATEGORY.get(product_type)
        if category:
            return category
        return PRODUCT_GROUP_CATEGORY.get(normalise(product.get("category")))

    # ---------------------------------------------------------
    # MAIN RERANKING
    # ---------------------------------------------------------

    def rerank(
        self,
        query,
        results,
        limit=10,
        max_category_ratio=0.35,
        session_intent=None,
    ):
        if not results or limit <= 0:
            return []

        query_tokens = self._tokenize(query)
        attributes = extract_v2(query)
        query_category = attributes.get("category")
        query_types = attributes.get("product_types")

        # S4: downrank (never remove) children's products for adult queries.
        kids_penalty = (
            self.kids_penalty
            if self.kids_penalty and not allows_kids(query)
            else 0.0
        )

        # S3-lite: boost explicit pattern matches, only inside a detected
        # category so S1's type tiers bound the reordering.
        pattern_requirements = (
            extract_patterns(query)
            if self.attribute_boost and query_category
            else []
        )

        scored = []

        for position, item in enumerate(results):
            product = item.get("product", {})

            # Hard category filter (S1): a product passes if it is one of the
            # named types or belongs to the query's broad category.
            specific = False
            if query_category:
                if query_types:
                    specific = normalise(product.get("product_type")) in query_types
                if not specific and self._infer_product_category(product) != query_category:
                    continue

            distance = float(item.get("distance", 0.0))

            semantic_score = self._semantic_score(distance)
            keyword_score = self._keyword_score(query_tokens, product)
            attribute_score = self._attribute_score(product, attributes)
            intent_score = self._product_intent_score(product, session_intent)
            occasion_score = self._occasion_score(query, product)
            query_match_score = self._query_match_score(query, product)

            # Identical to the v1 formula.
            final_score = (
                self.weights["semantic"] * semantic_score
                + self.weights["keyword"] * keyword_score
                + self.weights["attributes"] * attribute_score
                + self.weights["intent"] * intent_score
                + 0.10 * occasion_score
                + 0.15 * query_match_score
            )

            if kids_penalty and self._is_kids_product(product):
                final_score -= kids_penalty

            if pattern_requirements:
                final_score += PATTERN_BOOST * self._pattern_match_fraction(
                    product, pattern_requirements
                )

            scored.append(
                {
                    **item,
                    "_position": position,
                    "_specific": specific,
                    "_semantic_score": semantic_score,
                    "_keyword_score": keyword_score,
                    "_attribute_score": attribute_score,
                    "_intent_score": intent_score,
                    "_final_score": final_score,
                }
            )

        scored.sort(key=_sort_key)
        deduplicated = self._apply_deduplication(scored)

        if query_category and query_types:
            # Specific types first, then broad-category backfill.
            primary = [x for x in deduplicated if x["_specific"]]
            backfill = [x for x in deduplicated if not x["_specific"]]
            selected = (primary + backfill)[:limit]
        elif query_category:
            selected = deduplicated[:limit]
        else:
            selected = self._apply_diversity_v2(
                deduplicated, limit, max_category_ratio
            )
            selected.sort(key=_sort_key)

        return [
            self._format_result(rank, item, query, attributes, session_intent)
            for rank, item in enumerate(selected, start=1)
        ]

    # ---------------------------------------------------------
    # S2: diversity cap with backfill
    # ---------------------------------------------------------

    def _apply_diversity_v2(self, scored, limit, max_category_ratio):
        max_per_category = max(2, int(limit * max_category_ratio))

        counts = defaultdict(int)
        selected, skipped = [], []

        for item in scored:
            if len(selected) >= limit:
                break
            category = self._infer_product_category(item["product"]) or "unknown"
            if counts[category] >= max_per_category:
                skipped.append(item)
                continue
            selected.append(item)
            counts[category] += 1

        # Backfill from skipped candidates, best first. Items are unique
        # (each candidate is either selected or skipped), so no duplicates.
        for item in skipped:
            if len(selected) >= limit:
                break
            selected.append(item)

        return selected[:limit]

    # ---------------------------------------------------------
    # RESPONSE (same shape as v1)
    # ---------------------------------------------------------

    def _format_result(self, rank, item, query, attributes, session_intent):
        product = item["product"]
        return {
            "rank": rank,
            "article_id": item["article_id"],
            "score": round(item["_final_score"], 4),
            "semantic_score": round(item["_semantic_score"], 4),
            "keyword_score": round(item["_keyword_score"], 4),
            "attribute_score": round(item["_attribute_score"], 4),
            "intent_score": round(item["_intent_score"], 4),
            "distance": round(float(item["distance"]), 4),
            "reason": self._build_reason(
                query=query,
                product=product,
                attributes=attributes,
                session_intent=session_intent,
            ),
            "product": product,
        }
