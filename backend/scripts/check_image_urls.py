import asyncio
import httpx
from database.connection import get_database


async def check_images():
    db = get_database()
    products = await db["products"].find(
        {},
        {"_id": 1, "name": 1, "image": 1},
    ).to_list(length=None)

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=12.0,
    ) as client:
        for product in products:
            name = product.get("name", "Unknown")
            url = product.get("image")

            if not url:
                print(f"MISSING | {name} | No image URL")
                continue

            try:
                response = await client.get(url)
                content_type = response.headers.get(
                    "content-type", ""
                )
                works = (
                    response.status_code == 200
                    and content_type.startswith("image/")
                )
                status = "OK" if works else "CHECK"
                print(
                    f"{status} | {name} | "
                    f"HTTP {response.status_code} | "
                    f"{content_type} | {url}"
                )
            except Exception as exc:
                print(
                    f"ERROR | {name} | "
                    f"{type(exc).__name__}: {exc}"
                )


if __name__ == "__main__":
    asyncio.run(check_images())
