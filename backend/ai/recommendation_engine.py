import random

from search import semantic_search


class RecommendationEngine:
    """
    AI-powered recommendation engine.
    Removes duplicate products and enriches them for the frontend.
    """

    from search import semantic_search


class RecommendationEngine:
    """
    Semantic product recommendations using available catalog data.
    Avoids generating fake prices, ratings, reviews, or images.
    """

    async def recommend(self, query: str, limit: int = 10):
        products = await semantic_search(query)

        recommendations = []
        seen_names = set()

        for product in products:
            # Copy to avoid modifying the original search result.
            product = dict(product)

            name = str(product.get("name") or "").strip()

            if not name:
                continue

            # Remove duplicate names, ignoring case.
            name_key = name.casefold()

            if name_key in seen_names:
                continue

            seen_names.add(name_key)

            # Preserve actual catalog data.
            # Do not invent missing prices, ratings, reviews, or images.
            category = product.get("category")

            if category:
                product["reason"] = (
                    f"Recommended because it matches your search "
                    f"in the {category} category."
                )
            else:
                product["reason"] = (
                    "Recommended based on semantic similarity to your search."
                )

            recommendations.append(product)

            if len(recommendations) >= max(1, limit):
                break

        return recommendations

    def get_reason(self, product):

        category = product.get("category", "")

        if category:
            return (
                f"Recommended because it closely matches your search "
                f"in the {category} category."
            )

        return "Recommended based on semantic similarity."