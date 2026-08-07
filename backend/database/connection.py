from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import settings

_client: Optional[AsyncIOMotorClient] = None


async def connect_db() -> None:
    """Open the MongoDB connection pool. Called on app startup."""
    global _client
    _client = AsyncIOMotorClient(settings.mongodb_url)
    # Ping to confirm the connection is live
    await _client.admin.command("ping")
    print(f"✅ Connected to MongoDB: {settings.database_name}")


async def close_db() -> None:
    """Close the MongoDB connection pool. Called on app shutdown."""
    global _client
    if _client:
        _client.close()
        print("🔌 MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    """Return the application database. Raises if connect_db() was not called."""
    if _client is None:
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return _client[settings.database_name]
