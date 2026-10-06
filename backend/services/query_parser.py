import re


COLORS = {
    "black", "white", "red", "blue", "green",
    "yellow", "pink", "purple", "orange",
    "brown", "grey", "gray", "beige", "navy"
}


GENDER_ALIASES = {
    "women": "women",
    "woman": "women",
    "womens": "women",
    "ladies": "women",
    "lady": "women",
    "men": "men",
    "man": "men",
    "mens": "men",
    "male": "men",
    "unisex": "unisex",
}


class QueryParser:

    @staticmethod
    def extract(query: str) -> dict:
        text = query.lower().strip()

        return {
            "category": QueryParser._extract_category(text),
            "color": QueryParser._extract_color(text),
            "gender": QueryParser._extract_gender(text),
            "budget": QueryParser._extract_budget(text),
        }

    @staticmethod
    def _extract_category(text):
        category_keywords = {
            "outerwear": [
                "coat", "jacket", "blazer", "parka",
                "overcoat", "trench", "puffer", "bomber"
            ],
            "tops": [
                "top", "shirt", "blouse", "t-shirt",
                "tshirt", "tee", "tank", "camisole", "polo"
            ],
            "trousers": [
                "trousers", "pants", "jeans",
                "leggings", "shorts", "chinos", "joggers"
            ],
            "footwear": [
                "shoes", "sneakers", "boots",
                "sandals", "heels", "loafers"
            ],
            "bags": [
                "bag", "backpack", "handbag",
                "tote", "purse", "clutch"
            ],
            "swimwear": [
                "swimwear", "swimsuit",
                "bikini", "tankini", "beachwear"
            ],
            "knitwear": [
                "knitwear", "sweater",
                "jumper", "pullover", "cardigan"
            ],
        }

        for category, keywords in category_keywords.items():
            if any(re.search(rf"\b{re.escape(keyword)}\b", text)
                   for keyword in keywords):
                return category

        return None

    @staticmethod
    def _extract_color(text):
        for color in COLORS:
            if re.search(rf"\b{re.escape(color)}\b", text):
                if color == "gray":
                    return "grey"
                return color

        return None

    @staticmethod
    def _extract_gender(text):
        for word, gender in GENDER_ALIASES.items():
            if re.search(rf"\b{re.escape(word)}\b", text):
                return gender

        return None

    @staticmethod
    def _extract_budget(text):
        match = re.search(
            r"(?:under|below|less than|up to|around)\s*\$?\s*(\d+)",
            text
        )

        if match:
            return float(match.group(1))

        return None


query_parser = QueryParser()