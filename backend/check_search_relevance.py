import asyncio

from search import semantic_search


async def main():
    queries = [
        "Find white sneakers for everyday use",
        "white sneakers",
        "rain jacket for winter",
    ]

    for query in queries:
        print(f"\nQUERY: {query}")
        results = await semantic_search(query, top_k=10)

        for item in results:
            product = item.get("product", {})
            print(
                f"- {product.get('name')} | "
                f"type={product.get('product_type')} | "
                f"category={product.get('category')} | "
                f"distance={item.get('distance')}"
            )


if __name__ == "__main__":
    asyncio.run(main())