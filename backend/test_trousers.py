import asyncio

from services.product_service import ProductService


async def test():
    service = ProductService()

    result = await service.list_products(
        page=1,
        page_size=100,
        max_price=200,
        sort="price-asc"
    )

    print("\n--- PRODUCTS UNDER $200 ---")

    for product in result["items"]:
        print(
            product["name"],
            "|",
            product["category"],
            "| $",
            product["price"]
        )


if __name__ == "__main__":
    asyncio.run(test())