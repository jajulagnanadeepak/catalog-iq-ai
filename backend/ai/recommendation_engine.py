import random

from search import semantic_search


class RecommendationEngine:
    """
    AI-powered recommendation engine.
    Removes duplicate products and enriches them for the frontend.
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

            # ---------- Enrich Product ----------

            product["brand"] = product.get("department", "H&M")

            price = random.randint(999, 4999)

            product["price"] = price
            product["original_price"] = price + random.randint(300, 1200)

            product["rating"] = round(random.uniform(4.1, 5.0), 1)

            product["reviews"] = random.randint(50, 5000)

            product["image"] = (
                f"https://placehold.co/300x400?text="
                f"{name.replace(' ', '+')}"
            )

            # ---------- AI Fields ----------

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
            return (
                f"Recommended because it closely matches your search "
                f"in the {category} category."
            )

        return "Recommended based on semantic similarity."