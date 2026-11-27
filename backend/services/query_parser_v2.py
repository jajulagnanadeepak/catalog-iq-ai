"""Query attribute extraction for search v2 (Phase 1, S1).

Same output keys as ``QueryParser.extract`` (v1) plus ``product_types``.
Colour, gender and budget reuse the unchanged v1 helpers; only category
detection is new:

* the vocabulary comes from the catalogue's own product types
  (``services.catalog_vocabulary``);
* the longest phrase wins ("bikini top" beats "top");
* among non-overlapping matches the right-most one wins, i.e. the head noun
  ("polo shirt", "t-shirt dress", "dress shoes").
"""

import re

from services.catalog_vocabulary import QUERY_TERMS
from services.query_parser import QueryParser

# Longest phrases first, so overlap resolution keeps the most specific one.
_PATTERNS = [
    (
        phrase,
        re.compile(rf"(?<![\w-]){re.escape(phrase)}(?:s|es)?(?![\w-])"),
    )
    for phrase in sorted(QUERY_TERMS, key=lambda p: (-len(p), p))
]


def extract_category(text: str) -> tuple[str | None, frozenset | None]:
    """Return ``(category, product_types)`` for a lower-cased query."""
    taken: list[tuple[int, int, str]] = []

    for phrase, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span()
            if any(start < t_end and t_start < end for t_start, t_end, _ in taken):
                continue
            taken.append((start, end, phrase))

    if not taken:
        return None, None

    # Right-most surviving match is the head noun.
    _, _, phrase = max(taken, key=lambda t: t[0])
    return QUERY_TERMS[phrase]


def extract_v2(query: str) -> dict:
    text = query.lower().strip()
    category, product_types = extract_category(text)

    return {
        "category": category,
        "product_types": product_types,
        "color": QueryParser._extract_color(text),
        "gender": QueryParser._extract_gender(text),
        "budget": QueryParser._extract_budget(text),
    }
