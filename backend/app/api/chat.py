import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.trials import _verify_membership
from app.auth.dependencies import get_current_user
from app.chat.service import chat_turn
from app.database.models import ChatMessage, ChatThread, User
from app.database.session import get_db
from app.vector_db.client import get_qdrant

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    thread_id: str | None = None
    query: str


class ThreadResponse(BaseModel):
    id: str
    title: str
    created_by: str
    created_at: str
    updated_at: str


class CitationResponse(BaseModel):
    id: str
    chunk_id: str
    citation_index: int
    document_id: str
    content_excerpt: str | None
    page_number: int | None
    relevance_score: float | None


class MessageResponse(BaseModel):
    id: str
    thread_id: str
    role: str
    content: str
    grounding_failure: bool
    citations: list[CitationResponse]
    created_at: str


@router.post("/api/trials/{trial_id}/chat")
async def chat(
    trial_id: uuid.UUID,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_membership(trial_id, current_user.id, db)

    async def event_stream():
        async with get_qdrant() as qdrant:
            async for event in chat_turn(
                db=db,
                qdrant=qdrant,
                trial_id=str(trial_id),
                thread_id=body.thread_id,
                query=body.query,
                user=current_user,
            ):
                yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/trials/{trial_id}/threads", response_model=list[ThreadResponse])
async def list_threads(
    trial_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ThreadResponse]:
    await _verify_membership(trial_id, current_user.id, db)
    result = await db.execute(
        select(ChatThread)
        .where(ChatThread.trial_id == trial_id)
        .order_by(ChatThread.updated_at.desc())
    )
    threads = result.scalars().all()
    return [
        ThreadResponse(
            id=str(t.id),
            title=t.title,
            created_by=str(t.created_by),
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat(),
        )
        for t in threads
    ]


@router.post(
    "/api/trials/{trial_id}/threads",
    response_model=ThreadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_thread(
    trial_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThreadResponse:
    await _verify_membership(trial_id, current_user.id, db)
    thread = ChatThread(
        trial_id=trial_id,
        title="New Chat",
        created_by=current_user.id,
    )
    db.add(thread)
    await db.flush()
    await db.refresh(thread)
    return ThreadResponse(
        id=str(thread.id),
        title=thread.title,
        created_by=str(thread.created_by),
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat(),
    )


@router.delete("/api/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatThread).where(ChatThread.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    await _verify_membership(thread.trial_id, current_user.id, db)
    await db.delete(thread)
    await db.flush()


@router.get("/api/threads/{thread_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    thread_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageResponse]:
    result = await db.execute(
        select(ChatThread).where(ChatThread.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    await _verify_membership(thread.trial_id, current_user.id, db)

    msg_result = await db.execute(
        select(ChatMessage)
        .options(selectinload(ChatMessage.citations))
        .where(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.created_at)
    )
    messages = msg_result.scalars().all()

    return [
        MessageResponse(
            id=str(m.id),
            thread_id=str(m.thread_id),
            role=m.role,
            content=m.content,
            grounding_failure=m.grounding_failure,
            citations=[
                CitationResponse(
                    id=str(c.id),
                    chunk_id=str(c.chunk_id),
                    citation_index=c.citation_index,
                    document_id=str(c.document_id),
                    content_excerpt=c.content_excerpt,
                    page_number=c.page_number,
                    relevance_score=c.relevance_score,
                )
                for c in m.citations
            ],
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]
