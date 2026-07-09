import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from qdrant_client.models import Distance, VectorParams

from app.config import settings

logger = structlog.get_logger()


async def ensure_collection(client: AsyncQdrantClient) -> None:
    collections = await client.get_collections()
    names = {c.name for c in collections.collections}

    if settings.vector_collection_name not in names:
        await client.create_collection(
            collection_name=settings.vector_collection_name,
            vectors_config=VectorParams(
                size=settings.embedding_dimensions,
                distance=Distance.COSINE,
            ),
        )

        await client.create_payload_index(
            collection_name=settings.vector_collection_name,
            field_name="trial_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        await client.create_payload_index(
            collection_name=settings.vector_collection_name,
            field_name="document_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        await client.create_payload_index(
            collection_name=settings.vector_collection_name,
            field_name="chunk_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )

        logger.info("collection_created", name=settings.vector_collection_name)
    else:
        logger.info("collection_already_exists", name=settings.vector_collection_name)

    try:
        await client.create_payload_index(
            collection_name=settings.vector_collection_name,
            field_name="content",
            field_schema=models.PayloadSchemaType.TEXT,
        )
        logger.info("content_text_index_created")
    except Exception:
        logger.info("content_text_index_already_exists")
