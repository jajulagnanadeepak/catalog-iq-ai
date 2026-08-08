from search import semantic_search


class RecommendationEngine:
    """
    AI-powered recommendation engine.
    Removes duplicate products and adds recommendation scores.
    """

    async def recommend(self, query: str, limit: int = 10):

        products = await semantic_search(query)

        recommendations = []
        seen_names = set()

        score = 100

        for product in products:

            name = product.get("name", "").strip()

            # Skip duplicate product names
            if name in seen_names:
                continue

            seen_names.add(name)

            product["recommendation_score"] = max(score, 70)
            product["reason"] = self.get_reason(product)

            recommendations.append(product)

            score -= 2

            if len(recommendations) >= limit:
                break

        return recommendations

    def get_reason(self, product):

        category = product.get("category", "")

        if category:
            return f"Recommended because it closely matches your search in the {category} category."

        return "Recommended based on semantic similarity."