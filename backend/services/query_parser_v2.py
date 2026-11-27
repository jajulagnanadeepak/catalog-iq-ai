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

from services.catalog_vocabulary import (
    ADULT_PHRASES,
    AMBIGUOUS_AUDIENCE_TERMS,
    KIDS_QUERY_TERMS,
    QUERY_TERMS,
)
from services.query_parser import QueryParser


def _terms_pattern(terms):
    alternatives = "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True))
    # Longest first, so "children's" wins over "children"; a trailing
    # apostrophe ("kids' shoes") still counts as a word boundary.
    return re.compile(rf"(?<![\w-])(?:{alternatives})(?![\w-])")


_ADULT_PHRASES = _terms_pattern(ADULT_PHRASES)
_KIDS_OR_AMBIGUOUS = _terms_pattern(KIDS_QUERY_TERMS + AMBIGUOUS_AUDIENCE_TERMS)


def allows_kids(query: str) -> bool:
    """S4: True when children's products must not be downranked, i.e. the
    query names children ("girls party dress") or its audience is unclear
    ("teen hoodie", "dress for my daughter"). Adult phrases that merely
    contain a kids word ("baby pink", "girls' night", "babydoll") don't count.
    """
    text = _ADULT_PHRASES.sub(" ", " ".join(str(query).lower().split()))
    return bool(_KIDS_OR_AMBIGUOUS.search(text))

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
