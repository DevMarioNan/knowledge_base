from collections.abc import AsyncGenerator

from qdrant_client import AsyncQdrantClient

from app.config import settings


async def get_qdrant() -> AsyncGenerator[AsyncQdrantClient, None]:
    client = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )
    try:
        yield client
    finally:
        await client.close()
