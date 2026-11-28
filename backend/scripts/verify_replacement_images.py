import asyncio
import httpx

# The seeded images for p-001 and p-005 (database/seed.py), the same URLs as
# the frontend mock (src/lib/api/mock.ts).
urls = {
    "p-001 Mercer Wool Overcoat": "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?auto=format&fit=crop&w=800&q=80",
    "p-005 Terry Polo Shirt": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=800&q=80",
}

async def main():
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        for name, url in urls.items():
            try:
                response = await client.get(url)
                content_type = response.headers.get("content-type", "")
                valid = response.status_code == 200 and content_type.startswith("image/")
                print(f"{name}: {'OK' if valid else 'CHECK'} | HTTP {response.status_code} | {content_type}")
            except Exception as exc:
                print(f"{name}: ERROR | {type(exc).__name__}: {exc}")

asyncio.run(main())
