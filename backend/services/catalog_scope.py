"""Catalogue scope: hard out-of-catalogue detection (Phase 1, S5 hard tier).

A query is out of catalogue only when ALL of these hold; otherwise it is
treated as a normal search (fail safe):

1. S1 detects no fashion category (``extract_v2(query)["category"] is None``);
2. no catalogue product-type phrase (from the catalogue's own 131 types) and
   no generic accessory head ("case", "sleeve", "bag", ...) is present;
3. an explicit unsupported-domain phrase is present
   (``catalog_vocabulary.UNSUPPORTED_DOMAINS``).

Matching is whole-phrase with word boundaries (a hyphen counts as part of a
word), never substrings. No embeddings or distances are used, so the check
runs before FAISS retrieval.
"""

import re
from dataclasses import dataclass

from services.catalog_vocabulary import (
    GENERIC_ACCESSORY_HEADS,
    PRODUCT_TYPE_CATEGORY,
    UNSUPPORTED_DOMAINS,
    normalise,
)
from services.query_parser_v2 import extract_v2

REASON_PREFIX = "unsupported_domain:"


@dataclass(frozen=True)
class ScopeResult:
    out_of_catalog: bool
    reason: str | None = None


IN_CATALOG = ScopeResult(False)


def _expand_type(product_type: str) -> set[str]:
    """Catalogue type name -> phrases a shopper might type.

    "hat/beanie" -> hat, beanie; "hair/alice band" -> hair band, alice band;
    "pyjama jumpsuit/playsuit" -> pyjama jumpsuit, pyjama playsuit.
    Singular and plural forms are both included ("costumes" -> "costume").
    """
    if "/" in product_type:
        left, right = (p.split() for p in product_type.split("/", 1))
        if len(left) == 1 and len(right) > 1:
            parts = [" ".join(left + right[1:]), " ".join(right)]
        elif len(left) > 1 and len(right) == 1:
            parts = [" ".join(left), " ".join(left[:-1] + right)]
        else:
            parts = [" ".join(left), " ".join(right)]
    else:
        parts = [product_type]

    forms = set()
    for p in parts:
        forms.add(p)
        forms.add(p[:-1] if p.endswith("s") else p + "s")
    return {f for f in forms if f}


def _phrase_regex(phrases) -> re.Pattern:
    alternatives = "|".join(re.escape(p) for p in sorted(phrases, key=len, reverse=True))
    return re.compile(rf"(?<![\w-])(?:{alternatives})(?![\w-])")


CATALOGUE_PHRASES = frozenset(
    phrase
    for product_type in PRODUCT_TYPE_CATEGORY
    for phrase in _expand_type(product_type)
) | frozenset(GENERIC_ACCESSORY_HEADS)

_CATALOGUE_RX = _phrase_regex(CATALOGUE_PHRASES)

_DOMAIN_OF = {
    normalise(phrase): domain
    for domain, phrases in UNSUPPORTED_DOMAINS.items()
    for phrase in phrases
}
_DOMAIN_RX = _phrase_regex(_DOMAIN_OF)


def classify(query: str) -> ScopeResult:
    """Hard out-of-catalogue decision for a search query."""
    text = normalise(query)
    if not text:
        return IN_CATALOG

    # 1. A recognised fashion category always means "search normally".
    if extract_v2(text)["category"]:
        return IN_CATALOG

    # 2. Anything the catalogue sells by name, or a generic accessory.
    if _CATALOGUE_RX.search(text):
        return IN_CATALOG

    # 3. An explicit unsupported-domain phrase; reason from the first one.
    match = _DOMAIN_RX.search(text)
    if not match:
        return IN_CATALOG
    return ScopeResult(True, REASON_PREFIX + _DOMAIN_OF[match.group(0)])
