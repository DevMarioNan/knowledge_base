# Phase 3 — Detailed Implementation Plan

## Overview

9 sequential steps building the full RAG pipeline: retrieval (hybrid search + rerank) → prompt construction → chat orchestration with SSE streaming → frontend chat UI with citations.

---

## Step 1: Database Models + Migration — Threads & Messages

**Files:**
- `backend/app/database/models.py` — add `ChatThread`, `ChatMessage`, `MessageCitation`
- `backend/alembic/versions/0004_add_chat_models.py`

**Models:**

```
ChatThread:
  id: UUID PK
  trial_id: UUID FK(trials.id)
  title: str (auto-generated)
  created_by: UUID FK(users.id)
  created_at, updated_at

ChatMessage:
  id: UUID PK
  thread_id: UUID FK(threads.id, CASCADE)
  role: str ("user" | "assistant")
  content: str
  grounding_failure: bool (default false)
  created_at

MessageCitation:
  id: UUID PK
  message_id: UUID FK(messages.id, CASCADE)
  chunk_id: UUID
  citation_index: int ([n] in response)
  document_id: UUID
  content_excerpt: str | None
  page_number: int | None
  relevance_score: float | None
  created_at
```

---

## Step 2: Qdrant Full-Text Index for BM25

**File:** `backend/app/vector_db/setup.py`

Add a `TEXT` payload index on `content` field:
```python
field_name="content", field_schema=models.PayloadSchemaType.TEXT
```

Currently only `KEYWORD` indexes exist. Without this, Qdrant's built-in BM25 search won't work.

---

## Step 3: LLM Wrapper (`app/llm/`)

**Files to create:**
- `backend/app/llm/client.py` — OpenAI chat completion wrapper
- `backend/app/llm/tokens.py` — token counting utility

**`client.py` exports:**
```python
async def generate(
    messages: list[dict],
    model: str = settings.llm_model,
    stream: bool = False,
    max_tokens: int = 2048,
    temperature: float = 0.0,
) -> str | AsyncIterator[str]:
```

- Reuses module-level OpenAI client pattern from `embedder.py`
- `stream=True` returns `AsyncIterator[str]` (token chunks)
- Includes basic retry (1 retry on 429/5xx)

**`tokens.py` exports:**
```python
def count_tokens(text: str) -> int:  # uses tiktoken
def truncate_to_token_limit(text: str, limit: int) -> str:
def context_window_available(messages: list[dict], model_max: int) -> int:
```

---

## Step 4: Prompt System (`app/prompts/`)

**Files to create:**
- `backend/app/prompts/system.py` — system prompt template
- `backend/app/prompts/builder.py` — prompt assembly

System prompt instructions:
- Answer ONLY from provided context
- Say "I don't know based on the provided documents" if context is insufficient
- Cite sources as `[n]` referencing context item numbers
- May cite multiple sources: `[1][2]`

**`builder.py` exports:**
```python
def build_system_prompt() -> str
def build_context(chunks: list[RetrievedChunk]) -> str
def build_messages(query, chunks, history=None) -> list[dict]
```

---

## Step 5: Retrieval Pipeline (`app/retrieval/`)

**Files to create:**
- `backend/app/retrieval/types.py` — `RetrievedChunk` dataclass
- `backend/app/retrieval/hybrid.py` — dense + BM25 search + RRF fusion
- `backend/app/retrieval/reranker.py` — Cohere rerank wrapper
- `backend/app/retrieval/service.py` — top-level `retrieve()` orchestrator

**Approach:**
1. Generate query embedding via `embed_texts`
2. Dense search: `qdrant.search()` with cosine similarity + trial_id filter
3. BM25 search: `qdrant.scroll()` or `qdrant.search()` with full-text filter on `content`
4. RRF fusion: `score = 1 / (k + rank)` — merge dense + sparse results
5. Cohere rerank on top-K → return top-N

---

## Step 6: Chat Orchestrator (`app/chat/`)

**Files to create:**
- `backend/app/chat/service.py` — turn orchestration
- `backend/app/chat/stream.py` — SSE event formatting
- `backend/app/chat/citations.py` — citation parsing + validation

**Orchestrator flow:**
1. Load or create thread (with membership check)
2. Save user message to DB
3. Retrieve chunks (call retrieval.service.retrieve)
4. Build prompt (call prompts.builder.build_messages)
5. Stream LLM response (call llm.client.generate with stream=True)
6. Parse `[n]` citations from streamed tokens
7. Save assistant message + citations to DB
8. Auto-generate thread title if first message (via LLM)
9. Yield SSE events

**SSE event types:**
```
event: token           → {"type": "token", "content": "..."}
event: citations       → {"type": "citations", "citations": [...]}
event: done            → {"type": "done", "message_id": "..."}
event: grounding_failure → {"type": "grounding_failure", "message": "..."}
event: error           → {"type": "error", "message": "..."}
```

**Citation validation:**
- Extract all `[n]` patterns from output
- Verify each `n` maps to a retrieved chunk
- Unmapped citations → strip + log warning
- No valid citations → flag as partial grounding failure

---

## Step 7: Chat API Router + SSE Endpoint

**File:** `backend/app/api/chat.py`

**Endpoints:**

```
GET    /api/trials/{trial_id}/threads          → list threads
POST   /api/trials/{trial_id}/threads          → create thread
GET    /api/threads/{thread_id}/messages       → list messages w/ citations
POST   /api/trials/{trial_id}/chat             → SSE streaming chat
```

**Registration:** Add `chat_router` to `main.py`.

**SSE StreamingResponse pattern:**
```python
StreamingResponse(event_stream(), media_type="text/event-stream",
    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
```

---

## Step 8: Frontend — SSE Stream Support + useChat Hook

**Files:**
- `frontend/src/hooks/useChat.ts` — SSE streaming hook
- `frontend/src/lib/api.ts` — add SSE event source method (using native `fetch` + `ReadableStream`)

**`useChat.ts` API:**
```typescript
function useChat(trialId: string) {
  messages, sendMessage(query, threadId?), isStreaming,
  threads, activeThread, setActiveThread, createThread,
  error, groundingFailure
}
```

---

## Step 9: Frontend — Chat UI Components

**New shadcn components:**
```bash
pnpm dlx shadcn@latest add scroll-area tooltip sheet
```

**Files to create:**
- `frontend/src/components/ChatPanel.tsx` — main chat container
- `frontend/src/components/MessageBubble.tsx` — message with parsed citations
- `frontend/src/components/CitationTooltip.tsx` — hover source excerpt
- `frontend/src/components/SourcePanel.tsx` — cited passage panel
- `frontend/src/components/GroundingFailure.tsx` — "I don't know" fallback
- `frontend/src/components/ThreadList.tsx` — conversation sidebar

**Registration:** Add "Chat" tab to `TrialDetailPage.tsx`.

**Citation rendering:** Parse `[n]` in message content → render as clickable superscript with tooltip showing source excerpt.

---

## Dependency Graph

```
Step 1 (DB models) ─────────────────────────────┐
Step 2 (Qdrant TEXT index) ─────────────────────┤
Step 3 (LLM wrapper) ───────────────────────────┤
Step 4 (Prompts) ───────────────────────────────┼──→ Step 6 (Chat orchestrator)
Step 5 (Retrieval) ─────────────────────────────┤
                                                 │
Step 7 (Chat API) ←─────────────────────────────┘
                                                 │
Steps 8 & 9 (Frontend) ←────────────────────────┘
```

Implementation order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9

---

## Key Decisions

| Decision | Choice |
|----------|--------|
| Streaming protocol | SSE (Server-Sent Events) over HTTP — simpler than WebSocket, works with standard load balancers |
| BM25 source | Qdrant built-in full-text search — avoids needing Elasticsearch |
| Thread title gen | LLM summarizes first user query → 5-word title; fallback to "Chat {date}" |
| Context window mgmt | Count tokens before sending; truncate lowest-scored chunks first |
| Citation validation | Every `[n]` must map to a retrieved chunk; strip invalid ones, warn |
| New frontend deps | Only shadcn `scroll-area`, `tooltip`, `sheet` — no new npm packages |

**This file should be deleted after Phase 3 is complete and all steps are verified.**
