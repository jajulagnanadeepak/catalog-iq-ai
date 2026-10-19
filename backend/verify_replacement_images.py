import asyncio
import httpx

urls = {
    "Image A": "https://plus.unsplash.com/premium_photo-1674719144570-0728faf14f96?q=80&w=687&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=NHwxMjA3fDA%3D",
    "Image B": "https://plus.unsplash.com/premium_photo-1718913936342-eaafff98834b?q=80&w=1172&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=NHwxMjA3fDA%3D",
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
