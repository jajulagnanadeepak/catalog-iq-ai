from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from config import settings


_client: Optional[AsyncIOMotorClient] = None


def _is_client_closed() -> bool:
    """
    Check whether the current MongoDB client has been closed.
    """
    global _client

    if _client is None:
        return True

    try:
        return bool(_client.delegate._closed)
    except AttributeError:
        return False


async def connect_db() -> None:
    """
    Open MongoDB connection pool.
    Called during FastAPI startup.
    """
    global _client

    # Reuse an active client
    if _client is not None and not _is_client_closed():
        try:
            await _client.admin.command("ping")
            return
        except Exception:
            try:
                _client.close()
            except Exception:
                pass

    _client = AsyncIOMotorClient(
        settings.mongodb_url,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000,
    )

    await _client.admin.command("ping")

    print(
        f"MongoDB connected: {settings.database_name}"
    )


async def close_db() -> None:
    """
    Close MongoDB connection pool during application shutdown.
    """
    global _client

    if _client is not None:
        try:
            _client.close()
        finally:
            _client = None

    print("MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    """
    Return the application database.

    If the client was closed because of a development
    reload, recreate the client so API requests don't
    reuse a closed MongoClient.
    """
    global _client

    if _client is None or _is_client_closed():
        _client = AsyncIOMotorClient(
            settings.mongodb_url,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
        )

        print(
            f"MongoDB client recreated: {settings.database_name}"
        )

    return _client[settings.database_name]