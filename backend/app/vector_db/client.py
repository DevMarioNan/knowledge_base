from contextlib import asynccontextmanager

from qdrant_client import AsyncQdrantClient

from app.config import settings


@asynccontextmanager
async def get_qdrant():
    client = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        check_compatibility=False,
    )
    try:
        yield client
    finally:
        await client.close()
