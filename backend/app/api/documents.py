import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.trials import _verify_membership
from app.auth.dependencies import get_current_user
from app.config import settings
from app.database.models import Document, DocumentChunk, User
from app.database.session import get_db
from app.ingestion.pipeline import process_document

router = APIRouter(tags=["documents"])


class DocumentResponse(BaseModel):
    id: str
    trial_id: str
    filename: str
    status: str
    metadata: dict | None
    error_message: str | None
    created_at: str
    updated_at: str


class DocumentDetailResponse(DocumentResponse):
    chunk_count: int


ALLOWED_EXTENSIONS = {".pdf"}
MAX_UPLOAD_SIZE = settings.max_upload_size_mb * 1024 * 1024


@router.get("/api/trials/{trial_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    trial_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    await _verify_membership(trial_id, current_user.id, db)
    result = await db.execute(
        select(Document).where(
            Document.trial_id == trial_id,
            Document.deleted_at.is_(None),
        ).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        DocumentResponse(
            id=str(d.id),
            trial_id=str(d.trial_id),
            filename=d.filename,
            status=d.status,
            metadata=d.metadata,
            error_message=d.error_message,
            created_at=d.created_at.isoformat(),
            updated_at=d.updated_at.isoformat(),
        )
        for d in docs
    ]


@router.post(
    "/api/trials/{trial_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    trial_id: uuid.UUID,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    await _verify_membership(trial_id, current_user.id, db)

    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid file type '{ext}'. Only PDF files are allowed.",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB.",
        )

    document = Document(
        trial_id=trial_id,
        filename=file.filename,
        status="uploaded",
    )
    db.add(document)
    await db.flush()
    await db.refresh(document)

    storage_dir = Path(settings.storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / f"{document.id}.pdf"
    file_path.write_bytes(content)

    background_tasks.add_task(process_document, document.id)

    return DocumentResponse(
        id=str(document.id),
        trial_id=str(document.trial_id),
        filename=document.filename,
        status=document.status,
        metadata=document.metadata,
        error_message=document.error_message,
        created_at=document.created_at.isoformat(),
        updated_at=document.updated_at.isoformat(),
    )


@router.get("/api/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentDetailResponse:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.deleted_at.is_(None),
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    await _verify_membership(document.trial_id, current_user.id, db)

    chunk_count_result = await db.execute(
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
    )
    chunk_count = chunk_count_result.scalar() or 0

    return DocumentDetailResponse(
        id=str(document.id),
        trial_id=str(document.trial_id),
        filename=document.filename,
        status=document.status,
        metadata=document.metadata,
        error_message=document.error_message,
        chunk_count=chunk_count,
        created_at=document.created_at.isoformat(),
        updated_at=document.updated_at.isoformat(),
    )


@router.delete("/api/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.deleted_at.is_(None),
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    await _verify_membership(document.trial_id, current_user.id, db)

    chunk_result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    )
    chunks = chunk_result.scalars().all()

    embedding_ids = [c.embedding_id for c in chunks if c.embedding_id]

    if embedding_ids:
        async with AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        ) as qdrant:
            await qdrant.delete(
                collection_name=settings.vector_collection_name,
                points_selector=[str(eid) for eid in embedding_ids],
            )

    for chunk in chunks:
        await db.delete(chunk)

    document.deleted_at = datetime.now(UTC)

    file_path = Path(settings.storage_path) / f"{document_id}.pdf"
    if file_path.exists():
        file_path.unlink()
