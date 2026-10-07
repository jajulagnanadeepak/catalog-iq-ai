import re
from typing import Optional

from services.product_service import ProductService


class BudgetService:
    """
    Handles budget-aware product discovery using the real
    products collection.
    """

    def __init__(self):
        self.product_service = ProductService()

    def parse_budget(self, query: str) -> Optional[dict]:
        """
        Extract currency and maximum budget.
        """

        text = query.lower().strip()

        patterns = [
            (r"₹\s*([\d,]+(?:\.\d+)?)", "INR"),
            (r"\brs\.?\s*([\d,]+(?:\.\d+)?)", "INR"),
            (r"\brupees?\s*([\d,]+(?:\.\d+)?)", "INR"),
            (r"\$\s*([\d,]+(?:\.\d+)?)", "USD"),
            (r"\busd\s*([\d,]+(?:\.\d+)?)", "USD"),
            (r"€\s*([\d,]+(?:\.\d+)?)", "EUR"),
            (r"\beur\s*([\d,]+(?:\.\d+)?)", "EUR"),
            (r"£\s*([\d,]+(?:\.\d+)?)", "GBP"),
            (r"\bgbp\s*([\d,]+(?:\.\d+)?)", "GBP"),
        ]

        for pattern, currency in patterns:
            match = re.search(pattern, text)

            if match:
                amount = float(
                    match.group(1).replace(",", "")
                )

                return {
                    "currency": currency,
                    "max_price": amount,
                }

        return None

    def extract_product_query(self, query: str) -> str:
        """
        Remove the budget portion from the user's query.

        Example:
        'shirts under $200'
        -> 'shirts'
        """

        text = query.lower().strip()

        text = re.sub(
            r"(under|below|less than)\s*"
            r"(₹|\$|€|£|rs\.?|usd|eur|gbp|rupees?)?\s*"
            r"[\d,]+(?:\.\d+)?",
            "",
            text,
        )

        text = re.sub(
            r"(₹|\$|€|£|rs\.?|usd|eur|gbp|rupees?)\s*"
            r"[\d,]+(?:\.\d+)?",
            "",
            text,
        )

        return text.strip()

    def normalize_search_terms(self, query: str) -> list[str]:
        """
        Normalize common shopping terms.
        """

        words = re.findall(
            r"[a-z0-9]+",
            query.lower()
        )

        aliases = {
            "shirts": ["shirt", "shirts"],
            "tshirts": ["tshirt", "tshirts"],
            "tees": ["tee", "tees"],
            "trousers": ["trouser", "trousers"],
            "pants": ["pant", "pants"],
            "shoes": ["shoe", "shoes"],
            "jackets": ["jacket", "jackets"],
            "bags": ["bag", "bags"],
            "dresses": ["dress", "dresses"],
        }

        terms = []

        for word in words:

            if len(word) <= 1:
                continue

            if word in aliases:
                terms.extend(aliases[word])
            else:
                terms.append(word)

        return terms

    def product_matches_query(
        self,
        product: dict,
        search_terms: list[str],
    ) -> bool:
        """
        Check whether the product matches the
        requested product type or keywords.
        """

        if not search_terms:
            return True

        searchable_text = " ".join(
            [
                str(product.get("name", "")),
                str(product.get("category", "")),
                str(product.get("brand", "")),
                " ".join(product.get("tags", [])),
                str(product.get("description", "")),
            ]
        ).lower()

        for term in search_terms:

            pattern = rf"\b{re.escape(term)}\b"

            if re.search(pattern, searchable_text):
                return True

        return False

    def rank_products(
        self,
        products: list[dict],
        search_terms: list[str],
        max_price: float,
    ) -> list[dict]:
        """
        Rank budget-filtered products using:

        - 45% query relevance
        - 25% rating
        - 15% popularity
        - 15% budget fit
        """

        ranked = []

        max_reviews = max(
            (
                product.get("reviews", 0)
                for product in products
            ),
            default=1,
        )

        for product in products:

            searchable_text = " ".join(
                [
                    str(product.get("name", "")),
                    str(product.get("category", "")),
                    str(product.get("brand", "")),
                    " ".join(product.get("tags", [])),
                    str(product.get("description", "")),
                ]
            ).lower()

            matched_terms = sum(
                1
                for term in search_terms
                if re.search(
                    rf"\b{re.escape(term)}\b",
                    searchable_text,
                )
            )

            relevance_score = (
                matched_terms / len(search_terms)
                if search_terms
                else 0.0
            )

            rating_score = (
                float(product.get("rating", 0)) / 5.0
            )

            popularity_score = (
                float(product.get("reviews", 0))
                / max_reviews
            )

            price = float(
                product.get("price", 0)
            )

            if max_price > 0:
                budget_score = max(
                    0.0,
                    1.0 - (price / max_price)
                )
            else:
                budget_score = 0.0

            final_score = (
                relevance_score * 0.45
                + rating_score * 0.25
                + popularity_score * 0.15
                + budget_score * 0.15
            )

            product["recommendation_score"] = round(
                final_score,
                4
            )

            ranked.append(product)

        ranked.sort(
            key=lambda product: product[
                "recommendation_score"
            ],
            reverse=True,
        )

        return ranked

    async def search(
        self,
        query: str,
        page_size: int = 10,
    ) -> dict:
        """
        Search products using both budget and
        product-query constraints.
        """

        budget = self.parse_budget(query)

        if not budget:
            return {
                "success": False,
                "message": (
                    "I couldn't determine the budget "
                    "from your request."
                ),
                "items": [],
            }

        if budget["currency"] != "USD":
            return {
                "success": False,
                "message": (
                    f"Your budget is in "
                    f"{budget['currency']}, but the current "
                    "product catalog is priced in USD."
                ),
                "currency": budget["currency"],
                "items": [],
            }

        product_query = self.extract_product_query(query)

        search_terms = self.normalize_search_terms(
            product_query
        )

        result = await self.product_service.list_products(
            page=1,
            page_size=100,
            max_price=budget["max_price"],
            sort="price-asc",
        )

        items = [
            product
            for product in result["items"]
            if self.product_matches_query(
                product,
                search_terms,
            )
        ]

        items = self.rank_products(
            products=items,
            search_terms=search_terms,
            max_price=budget["max_price"],
        )

        items = items[:page_size]

        return {
            "success": True,
            "currency": budget["currency"],
            "max_price": budget["max_price"],
            "query": product_query,
            "total": len(items),
            "items": items,
        }