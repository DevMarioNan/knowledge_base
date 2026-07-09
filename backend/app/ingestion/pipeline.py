import uuid
from pathlib import Path

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import Document, DocumentChunk
from app.database.session import async_session_factory
from app.ingestion.chunker import chunk_document
from app.ingestion.embedder import embed_texts
from app.ingestion.parser import parse_pdf

logger = structlog.get_logger()


async def process_document(document_id: uuid.UUID) -> None:
    logger.info("processing_document", document_id=str(document_id))

    async with async_session_factory() as db:
        try:
            result = await db.execute(select(Document).where(Document.id == document_id))
            document = result.scalar_one_or_none()
            if document is None:
                logger.error("document_not_found", document_id=str(document_id))
                return

            storage_dir = Path(settings.storage_path)
            file_path = storage_dir / f"{document_id}.pdf"

            if not file_path.exists():
                await _update_status(db, document, "failed", "File not found on disk")
                return

            document.status = "parsing"
            await db.flush()

            parse_result = await parse_pdf(file_path)

            document.status = "chunking"
            await db.flush()

            chunks = chunk_document(parse_result)

            document.status = "embedding"
            await db.flush()

            texts = [c.content for c in chunks]
            vectors = await embed_texts(texts)

            async with AsyncQdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
            ) as qdrant:
                points = []
                for chunk, vector in zip(chunks, vectors):
                    chunk_id = uuid.uuid4()
                    embedding_id = uuid.uuid4()

                    points.append(
                        PointStruct(
                            id=str(embedding_id),
                            vector=vector,
                            payload={
                                "chunk_id": str(chunk_id),
                                "document_id": str(document_id),
                                "trial_id": str(document.trial_id),
                                "page_number": chunk.page_number,
                                "section_title": chunk.section_title,
                                "section_number": chunk.section_number,
                                "source_filename": document.filename,
                                "content": chunk.content,
                                "chunk_index": chunk.chunk_index,
                            },
                        )
                    )

                    db.add(
                        DocumentChunk(
                            id=chunk_id,
                            document_id=document_id,
                            trial_id=document.trial_id,
                            chunk_index=chunk.chunk_index,
                            content=chunk.content,
                            token_count=chunk.token_count,
                            page_number=chunk.page_number,
                            section_title=chunk.section_title,
                            section_number=chunk.section_number,
                            embedding_id=embedding_id,
                        )
                    )

                await qdrant.upload_points(
                    collection_name=settings.vector_collection_name,
                    points=points,
                )

            document.status = "ready"
            if parse_result.metadata:
                existing = document.metadata or {}
                existing.update(parse_result.metadata)
                document.metadata = existing
            await db.flush()

            logger.info(
                "document_processed",
                document_id=str(document_id),
                chunk_count=len(chunks),
            )

        except Exception as exc:
            logger.error("document_processing_failed", document_id=str(document_id), error=str(exc))
            await _update_status(db, document, "failed", str(exc))
            raise


async def _update_status(
    db: AsyncSession, document: Document, status: str, error: str | None = None
) -> None:
    document.status = status
    if error:
        document.error_message = error
    await db.flush()
