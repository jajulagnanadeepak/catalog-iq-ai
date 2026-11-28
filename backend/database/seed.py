"""
Seed the demo ``products`` collection with the 12 catalogue products that
mirror the frontend mock (``_id`` ``p-001`` to ``p-012``).

Safety (Phase 1 WS-E3.6):
* importing this module does nothing (no DB connection, no reads, no writes);
* running it without flags is a dry run: it reports the target database, the
  existing document count (read-only) and the planned insert;
* ``--apply`` inserts the products, and only into an empty collection; it never
  updates, deletes or overwrites documents;
* ``APP_ENV=production`` is always refused before connecting, with no override
  (this is demo data);
* the MongoDB URL is never printed.

Usage (from ``backend/``):
    python -m database.seed            # dry run
    python -m database.seed --apply    # insert into an empty collection
"""

import argparse
import asyncio
import sys

from config import settings
from database.connection import connect_db, close_db, get_database

COLLECTION_NAME = "products"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_REFUSED = 2

PRODUCTS = [
    {
        "_id": "p-001",
        "name": "Mercer Wool Overcoat",
        "brand": "Arket",
        "category": "Outerwear",
        "price": 289.00,
        "original_price": 360.00,
        "rating": 4.8,
        "reviews": 214,
        "image": "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?auto=format&fit=crop&w=800&q=80",
        "colors": ["Camel", "Charcoal", "Navy"],
        "sizes": ["XS", "S", "M", "L", "XL"],
        "tags": ["wool", "overcoat", "winter", "layering"],
        "description": "Double-faced wool overcoat with notched lapel and concealed button closure.",
        "in_stock": True,
    },
    {
        "_id": "p-002",
        "name": "Linen Relaxed Shirt",
        "brand": "Sunspel",
        "category": "Tops",
        "price": 95.00,
        "rating": 4.5,
        "reviews": 88,
        "image": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=600",
        "colors": ["White", "Sky", "Sage"],
        "sizes": ["S", "M", "L", "XL"],
        "tags": ["linen", "shirt", "summer", "casual"],
        "description": "Relaxed-fit linen shirt with a curved hem and mother-of-pearl buttons.",
        "in_stock": True,
    },
    {
        "_id": "p-003",
        "name": "Slim Taper Chino",
        "brand": "NN07",
        "category": "Trousers",
        "price": 135.00,
        "rating": 4.6,
        "reviews": 157,
        "image": "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=600",
        "colors": ["Stone", "Navy", "Olive"],
        "sizes": ["28", "30", "32", "34", "36"],
        "tags": ["chino", "slim", "trousers", "office"],
        "description": "Tailored chino in stretch cotton blend. Slim-taper cut from hip to hem.",
        "in_stock": True,
    },
    {
        "_id": "p-004",
        "name": "Cotton Crew Sweatshirt",
        "brand": "Colorful Standard",
        "category": "Tops",
        "price": 79.00,
        "rating": 4.4,
        "reviews": 320,
        "image": "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?w=600",
        "colors": ["Burgundy", "Forest", "Steel Blue", "Cream"],
        "sizes": ["XS", "S", "M", "L", "XL", "XXL"],
        "tags": ["sweatshirt", "cotton", "casual", "everyday"],
        "description": "Heavyweight organic cotton crew sweatshirt with a brushed interior.",
        "in_stock": True,
    },
    {
        "_id": "p-005",
        "name": "Terry Polo Shirt",
        "brand": "Sunspel",
        "category": "Tops",
        "price": 110.00,
        "original_price": 130.00,
        "rating": 4.7,
        "reviews": 96,
        "image": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=800&q=80",
        "colors": ["White", "Navy"],
        "sizes": ["S", "M", "L", "XL"],
        "tags": ["polo", "terry", "summer"],
        "description": "Classic polo in towelling terry fabric. Retro cut with a ribbed collar.",
        "in_stock": True,
    },
    {
        "_id": "p-006",
        "name": "Leather Tote Bag",
        "brand": "Mismo",
        "category": "Bags",
        "price": 345.00,
        "rating": 4.9,
        "reviews": 74,
        "image": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=600",
        "colors": ["Cognac", "Black"],
        "sizes": ["One Size"],
        "tags": ["bag", "leather", "tote", "work"],
        "description": "Full-grain vegetable-tanned leather tote with a zip closure and laptop sleeve.",
        "in_stock": True,
    },
    {
        "_id": "p-007",
        "name": "Derby Shoe",
        "brand": "Grenson",
        "category": "Footwear",
        "price": 295.00,
        "rating": 4.7,
        "reviews": 112,
        "image": "https://images.unsplash.com/photo-1533867617858-e7b97e060509?w=600",
        "colors": ["Tan", "Black"],
        "sizes": ["40", "41", "42", "43", "44", "45"],
        "tags": ["shoes", "derby", "leather", "formal"],
        "description": "Goodyear-welted derby in pebble-grain leather. Triple leather sole.",
        "in_stock": True,
    },
    {
        "_id": "p-008",
        "name": "Merino Turtleneck",
        "brand": "John Smedley",
        "category": "Tops",
        "price": 175.00,
        "rating": 4.8,
        "reviews": 188,
        "image": "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=600",
        "colors": ["Oatmeal", "Black", "Navy", "Bordeaux"],
        "sizes": ["S", "M", "L", "XL"],
        "tags": ["merino", "turtleneck", "knitwear", "winter"],
        "description": "Fine-gauge 30-gauge Sea Island merino turtleneck. Fully fashioned.",
        "in_stock": True,
    },
    {
        "_id": "p-009",
        "name": "Swim Shorts",
        "brand": "Orlebar Brown",
        "category": "Swimwear",
        "price": 175.00,
        "original_price": 210.00,
        "rating": 4.5,
        "reviews": 63,
        "image": "https://images.unsplash.com/photo-1565084888279-aca607ecce0c?w=600",
        "colors": ["Navy", "Coastal Blue", "Sand"],
        "sizes": ["S", "M", "L", "XL"],
        "tags": ["swim", "shorts", "summer", "beach"],
        "description": "Tailored swim shorts with side-adjusters and a flat front.",
        "in_stock": True,
    },
    {
        "_id": "p-010",
        "name": "Canvas Chelsea Boot",
        "brand": "Common Projects",
        "category": "Footwear",
        "price": 490.00,
        "rating": 4.6,
        "reviews": 59,
        "image": "https://images.unsplash.com/photo-1638247025967-b4e38f787b76?w=600",
        "colors": ["Black", "White"],
        "sizes": ["40", "41", "42", "43", "44"],
        "tags": ["chelsea", "boot", "canvas", "minimalist"],
        "description": "Minimal canvas Chelsea boot with a gold serial number stamp.",
        "in_stock": True,
    },
    {
        "_id": "p-011",
        "name": "Field Jacket",
        "brand": "Nigel Cabourn",
        "category": "Outerwear",
        "price": 580.00,
        "rating": 4.9,
        "reviews": 41,
        "image": "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=600",
        "colors": ["Olive", "Khaki"],
        "sizes": ["S", "M", "L", "XL"],
        "tags": ["jacket", "field", "military", "outerwear"],
        "description": "Authentic vintage military field jacket in waxed cotton. British heritage.",
        "in_stock": True,
    },
    {
        "_id": "p-012",
        "name": "Down Puffer Jacket",
        "brand": "Canada Goose",
        "category": "Outerwear",
        "price": 695.00,
        "rating": 4.7,
        "reviews": 299,
        "image": "https://images.unsplash.com/photo-1547949003-9792a18a2601?w=600",
        "colors": ["Black", "Navy", "Red"],
        "sizes": ["XS", "S", "M", "L", "XL", "XXL"],
        "tags": ["puffer", "down", "winter", "warm", "outerwear"],
        "description": "Arctic-rated 625-fill power down puffer with a coyote-fur trimmed hood.",
        "in_stock": True,
    },
]


def _is_production() -> bool:
    return str(settings.app_env).strip().lower() == "production"


def _print_plan(existing: int) -> None:
    print("-" * 60)
    print(f"Target database   : {settings.database_name}")
    print(f"Target collection : {COLLECTION_NAME}")
    print(f"Existing documents: {existing:,}")
    if existing > 0:
        print("Planned operation : none (the seed only fills an empty collection)")
    else:
        print(
            f"Planned operation : insert {len(PRODUCTS)} demo products "
            f"({PRODUCTS[0]['_id']} to {PRODUCTS[-1]['_id']})"
        )
    print("-" * 60)


async def seed(apply: bool = False) -> int:
    print("=" * 60)
    print("CatalogIQ demo product seed")
    print("=" * 60)

    # Checked before any connection; there is deliberately no override.
    if _is_production():
        print(
            "REFUSED: APP_ENV=production. The demo seed never runs in production. "
            "Nothing was changed."
        )
        return EXIT_REFUSED

    try:
        try:
            await connect_db()
        except Exception as exc:
            # Only the exception type: driver messages can include the host.
            print(f"ERROR: could not connect to MongoDB ({type(exc).__name__}). Nothing was changed.")
            return EXIT_ERROR

        # Same collection name used by ProductService.
        collection = get_database()[COLLECTION_NAME]
        existing = await collection.count_documents({})
        _print_plan(existing)

        if existing > 0:
            print(
                f"SKIPPED: '{COLLECTION_NAME}' already has {existing:,} documents. "
                "Nothing was changed."
            )
            return EXIT_OK

        if not apply:
            print("DRY RUN: nothing was changed. Re-run with --apply to insert.")
            return EXIT_OK

        await collection.insert_many([dict(product) for product in PRODUCTS])
        print(
            f"Seeded {len(PRODUCTS)} products into "
            f"'{settings.database_name}.{COLLECTION_NAME}'."
        )
        return EXIT_OK

    except Exception as exc:
        print(
            f"ERROR: MongoDB operation failed ({type(exc).__name__}). "
            f"'{COLLECTION_NAME}' may hold some of the demo products; check it before re-running."
        )
        return EXIT_ERROR

    finally:
        await close_db()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            f"Seed the demo '{COLLECTION_NAME}' collection. "
            "Dry run unless --apply is given."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=f"insert the demo products (only into an empty '{COLLECTION_NAME}')",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    return asyncio.run(seed(apply=args.apply))


if __name__ == "__main__":
    sys.exit(main())