"""
Read-only catalog attribute lookup and relevance grading for the search eval.

Ground truth comes from `articles.csv` (the same source the catalog was
imported from). It is read with the standard library only; nothing is
written anywhere. Attributes not stored in MongoDB (`index_group_name`,
`perceived_colour_master_name`, `graphical_appearance_name`) are available
here, which is why the eval grades from the CSV rather than the API payload.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CSV = Path(__file__).resolve().parents[2] / "articles.csv"

KIDS_GROUP = "Baby/Children"

# How a query's audience maps onto H&M's index groups. "Sport" mixes
# genders, so its section name decides.
AUDIENCES = {"any", "adult", "women", "men", "kids"}


@dataclass(frozen=True)
class Item:
    article_id: str
    product_type: str
    product_group: str
    colour: str  # perceived_colour_master_name
    index_group: str
    section: str
    appearance: str  # graphical_appearance_name
    text: str  # lower-cased name + description

    @property
    def is_kids(self) -> bool:
        return self.index_group == KIDS_GROUP


def normalise_id(article_id) -> str:
    value = str(article_id).strip()
    return value.zfill(10) if value.isdigit() else value


def load_catalog(csv_path: Path | str = DEFAULT_CSV) -> dict[str, Item]:
    items: dict[str, Item] = {}
    with open(csv_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            aid = normalise_id(row["article_id"])
            items[aid] = Item(
                article_id=aid,
                product_type=row["product_type_name"],
                product_group=row["product_group_name"],
                colour=row["perceived_colour_master_name"],
                index_group=row["index_group_name"],
                section=row["section_name"],
                appearance=row["graphical_appearance_name"],
                text=f"{row['prod_name']} {row['detail_desc']}".lower(),
            )
    return items


def audience_ok(audience: str | None, item: Item) -> bool:
    if not audience or audience == "any":
        return True
    if audience == "kids":
        return item.is_kids
    if audience == "adult":
        return not item.is_kids
    section = item.section.lower()
    if audience == "women":
        if item.index_group in ("Ladieswear", "Divided"):
            return True
        return item.index_group == "Sport" and ("ladies" in section or "women" in section)
    if audience == "men":
        if item.index_group == "Menswear":
            return True
        return item.index_group == "Sport" and "men" in section and "women" not in section
    raise ValueError(f"unknown audience {audience!r}")


@dataclass(frozen=True)
class Grade:
    gain: float
    max_gain: float
    type_ok: bool
    related: bool
    colour_ok: bool | None
    audience_ok: bool | None
    attribute_ok: bool | None

    @property
    def fully_relevant(self) -> bool:
        """Exact type and every *hard* constraint (colour, audience). Attribute terms are soft."""
        return (
            self.type_ok
            and self.colour_ok is not False
            and self.audience_ok is not False
        )


def grade(expect: dict, item: Item | None) -> Grade:
    """
    Graded relevance of one result for one query spec.

    gain = 0 when the product type is wrong; 0.5 when only the product group
    is related (e.g. a jumpsuit for a dress query); otherwise
    1 + one point per specified constraint that is satisfied
    (colour, audience, attribute terms).
    """
    specified = [
        k for k in ("colours", "audience", "attribute_terms")
        if expect.get(k) and not (k == "audience" and expect[k] == "any")
    ]
    # attribute_appearances counts as part of attribute_terms
    if "attribute_terms" not in specified and expect.get("attribute_appearances"):
        specified.append("attribute_terms")
    max_gain = 1.0 + len(specified)

    if item is None:
        return Grade(0.0, max_gain, False, False, None, None, None)

    type_ok = item.product_type in expect.get("product_types", [])
    related = (not type_ok) and item.product_group in expect.get("related_groups", [])

    colour_ok = (item.colour in expect["colours"]) if "colours" in specified else None
    aud_ok = audience_ok(expect.get("audience"), item) if "audience" in specified else None
    attr_ok = None
    if "attribute_terms" in specified:
        terms = expect.get("attribute_terms") or []
        apps = expect.get("attribute_appearances") or []
        attr_ok = any(t in item.text for t in terms) or item.appearance in apps

    if type_ok:
        gain = 1.0 + sum(1 for v in (colour_ok, aud_ok, attr_ok) if v)
    elif related:
        gain = 0.5
    else:
        gain = 0.0
    return Grade(gain, max_gain, type_ok, related, colour_ok, aud_ok, attr_ok)


def gain_histogram(expect: dict, catalog: dict[str, Item]) -> dict[str, int]:
    """Count catalog items per achievable gain (for the ideal DCG)."""
    hist: dict[str, int] = {}
    for item in catalog.values():
        g = grade(expect, item).gain
        if g > 0:
            key = f"{g:g}"
            hist[key] = hist.get(key, 0) + 1
    return dict(sorted(hist.items(), key=lambda kv: -float(kv[0])))
