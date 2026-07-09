import uuid
from collections.abc import AsyncIterator

import structlog
from qdrant_client import AsyncQdrantClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.citations import parse_citations, validate_grounding
from app.chat.stream import (
    citations_event,
    done_event,
    error_event,
    grounding_failure_event,
    thread_event,
    token_event,
)
from app.database.models import ChatMessage, ChatThread, MessageCitation, TrialSettings, User
from app.llm.client import generate
from app.prompts.builder import build_messages
from app.retrieval.service import retrieve

logger = structlog.get_logger()


async def _create_thread(
    db: AsyncSession,
    trial_id: str,
    user_id: str,
    title: str = "New Chat",
) -> ChatThread:
    thread = ChatThread(
        trial_id=uuid.UUID(trial_id),
        title=title,
        created_by=uuid.UUID(user_id),
    )
    db.add(thread)
    await db.flush()
    await db.refresh(thread)
    return thread


async def _save_message(
    db: AsyncSession,
    thread_id: uuid.UUID,
    role: str,
    content: str,
    grounding_failure: bool = False,
) -> ChatMessage:
    message = ChatMessage(
        thread_id=thread_id,
        role=role,
        content=content,
        grounding_failure=grounding_failure,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message


async def _save_citations(
    db: AsyncSession,
    message_id: uuid.UUID,
    citations: list[dict],
) -> None:
    for cit in citations:
        db.add(MessageCitation(
            message_id=message_id,
            chunk_id=uuid.UUID(cit["chunk_id"]),
            citation_index=cit["citation_index"],
            document_id=uuid.UUID(cit["document_id"]),
            content_excerpt=cit.get("content_excerpt"),
            page_number=cit.get("page_number"),
            relevance_score=cit.get("relevance_score"),
        ))
    await db.flush()


async def _auto_generate_title(db: AsyncSession, thread_id: uuid.UUID, query: str) -> str:
    try:
        title_instruction = (
            "Generate a short title (max 6 words) for this question about "
            "clinical trial documents. Return ONLY the title, no punctuation."
        )
        title_gen = await generate(
            messages=[
                {"role": "system", "content": title_instruction},
                {"role": "user", "content": query},
            ],
            max_tokens=30,
            temperature=0.3,
        )
        raw = title_gen.strip().strip('"').strip("'") if isinstance(title_gen, str) else "New Chat"
        title = raw if raw.strip() else "New Chat"
        if len(title) > 60:
            title = title[:60]
    except Exception:
        title = "New Chat"

    result = await db.execute(select(ChatThread).where(ChatThread.id == thread_id))
    thread = result.scalar_one_or_none()
    if thread:
        thread.title = title
        await db.flush()
    return title


async def chat_turn(
    db: AsyncSession,
    qdrant: AsyncQdrantClient,
    trial_id: str,
    thread_id: str | None,
    query: str,
    user: User,
) -> AsyncIterator[str]:
    resolved_thread_id: uuid.UUID | None = None
    is_new_thread = False

    try:
        if thread_id:
            resolved_thread_id = uuid.UUID(thread_id)
            result = await db.execute(
                select(ChatThread).where(
                    ChatThread.id == resolved_thread_id,
                    ChatThread.trial_id == uuid.UUID(trial_id),
                )
            )
            thread = result.scalar_one_or_none()
            if not thread:
                yield await error_event("Thread not found")
                return
        else:
            thread = await _create_thread(db, trial_id, str(user.id))
            resolved_thread_id = thread.id
            is_new_thread = True
            await db.commit()

        await _save_message(db, resolved_thread_id, "user", query)
        await db.flush()

        result = await db.execute(
            select(TrialSettings).where(TrialSettings.trial_id == uuid.UUID(trial_id))
        )
        trial_settings = result.scalar_one_or_none()

        top_k = trial_settings.top_k_retrieval if trial_settings else 10
        top_n = trial_settings.top_n_rerank if trial_settings else 5
        rerank_model = trial_settings.cohere_rerank_model if trial_settings else None
        llm_model = trial_settings.llm_model if trial_settings else None

        retrieved_chunks = await retrieve(
            qdrant=qdrant,
            trial_id=trial_id,
            query=query,
            top_k=top_k,
            top_n=top_n,
            rerank_model=rerank_model,
        )

        messages = build_messages(query, retrieved_chunks)

        assistant_content_parts: list[str] = []
        streamer = await generate(
            messages=messages,
            model=llm_model,
            stream=True,
        )
        async for token_chunk in streamer:
            assistant_content_parts.append(token_chunk)
            yield await token_event(token_chunk)

        full_content = "".join(assistant_content_parts)

        citations = parse_citations(full_content, retrieved_chunks)
        is_grounded = validate_grounding(full_content, retrieved_chunks)

        if not is_grounded:
            yield await grounding_failure_event()
            assistant_msg = await _save_message(
                db, resolved_thread_id, "assistant", full_content, grounding_failure=True,
            )
        else:
            assistant_msg = await _save_message(
                db, resolved_thread_id, "assistant", full_content,
            )

        if citations:
            await _save_citations(db, assistant_msg.id, citations)
            yield await citations_event(citations)

        if is_new_thread:
            title = await _auto_generate_title(db, resolved_thread_id, query)
            yield await thread_event(str(resolved_thread_id), title)

        yield await done_event(str(assistant_msg.id))
        await db.commit()

    except Exception as exc:
        await db.rollback()
        logger.error("chat_turn_failed", error=str(exc))
        yield await error_event(str(exc))
