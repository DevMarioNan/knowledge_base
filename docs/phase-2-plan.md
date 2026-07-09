# Phase 2 Implementation Plan

> **⚠️ TEMPORARY FILE — DELETE AFTER PHASE 2 IS COMPLETE**

This file contains the implementation plan for Phase 2 (Trials & Document Ingestion). Once all items in `todo.md` Phase 2 are checked off, delete this file.

---

## 1. Backend: New DB Models + Migration

**Files:** `backend/app/database/models.py` (add 2 models), `backend/alembic/versions/0002_documents.py`

**`Document`** — table `documents`

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `trial_id` | FK → `trials.id` | |
| `filename` | `String(255)` | original filename |
| `status` | `String(50)` | `uploaded → parsing → chunking → embedding → ready / failed` |
| `metadata` | `JSON` | nullable, stores page count, file size, etc. |
| `error_message` | `Text` | nullable, reason if failed |
| `deleted_at` | `DateTime` | nullable — soft delete marker |
| `created_at` | `DateTime` | `server_default=func.now()` |
| `updated_at` | `DateTime` | `server_default+onupdate` |

**`DocumentChunk`** — table `document_chunks`

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `document_id` | FK → `documents.id` | cascade delete |
| `trial_id` | FK → `trials.id` | denormalized for Qdrant filtering |
| `chunk_index` | `Integer` | ordinal in document |
| `content` | `Text` | chunk text |
| `token_count` | `Integer` | nullable |
| `page_number` | `Integer` | nullable |
| `section_title` | `String(255)` | nullable |
| `section_number` | `String(50)` | nullable |
| `embedding_id` | `UUID` | nullable — the Qdrant point UUID (set after embed) |
| `created_at` | `DateTime` | `server_default=func.now()` |

Run: `uv run alembic revision --autogenerate -m "add documents and document_chunks"`, review, apply.

---

## 2. Backend: Qdrant Client + Collection Setup

**Files:** `backend/app/vector_db/client.py`, `backend/app/vector_db/setup.py`

- **`client.py`**: `AsyncQdrantClient(settings.qdrant_url, api_key=...)`. Expose `get_qdrant()` async generator.
- **`setup.py`**: `ensure_collection()` — check if `settings.vector_collection_name` exists, create if not with `size=settings.embedding_dimensions` (1536), `distance=Distance.COSINE`. Payload indexes on `trial_id`, `document_id`, `chunk_id`.
- Wire `ensure_collection()` into `lifespan` in `main.py`.

---

## 3. Backend: Trials API Router

**File:** `backend/app/api/trials.py`

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/trials` | List trials user is a member of |
| `POST` | `/api/trials` | Create trial + auto-add creator as admin |
| `GET` | `/api/trials/{id}` | Trial detail (verify membership) |
| `PUT` | `/api/trials/{id}` | Update name/description |
| `DELETE` | `/api/trials/{id}` | Delete trial (only creator) |

Membership endpoints (same file):

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/trials/{id}/members` | List members with user info |
| `POST` | `/api/trials/{id}/members` | Invite by email (lookup user, add member) |
| `DELETE` | `/api/trials/{id}/members/{user_id}` | Remove member (admin only) |

Register in `main.py`.

---

## 4. Backend: Document Endpoints

**File:** `backend/app/api/documents.py`

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/trials/{id}/documents` | List non-deleted documents for trial |
| `POST` | `/api/trials/{id}/documents` | Upload PDF (multipart, validate type + size) |
| `GET` | `/api/documents/{id}` | Document detail + status |
| `DELETE` | `/api/documents/{id}` | Soft delete + Qdrant chunk removal |

Upload flow: create `Document(status=uploaded)`, save file to `backend/storage/{doc_id}.pdf`, kick off `BackgroundTasks.add_task(process_document, doc_id)`, return document immediately.

Register in `main.py`.

---

## 5. Backend: Ingestion Pipeline

**Files:**
- `backend/app/ingestion/parser.py` — PDF parsing (PyMuPDF/fitz + pdfminer.six fallback)
- `backend/app/ingestion/chunker.py` — hybrid chunking (section-aware + recursive character fallback)
- `backend/app/ingestion/embedder.py` — OpenAI `text-embedding-3-small` embeddings
- `backend/app/ingestion/pipeline.py` — `process_document()` orchestration

**`pipeline.py` — `process_document(document_id: UUID)`:**
1. Update status → `parsing`
2. Parse PDF → raw chunks with metadata
3. Update status → `chunking`
4. Chunk text → final chunks
5. Update status → `embedding`
6. Embed chunks → vectors
7. Store in Qdrant (payload: chunk_id, document_id, trial_id, page_number, section_title, source_filename, text)
8. Save `DocumentChunk` rows in Postgres
9. Update status → `ready`
10. On error: status → `failed`, set `error_message`

Uses its own DB session (`async_session_factory()`) — not the request session.

---

## 6. Backend: New Dependencies

Add to `pyproject.toml`:
- `PyMuPDF` (fitz) — structure-aware PDF parsing
- `pdfminer.six` — fallback parser

---

## 7. Frontend: shadcn/ui Components

```bash
cd frontend && pnpm dlx shadcn@latest add card dialog input label separator table avatar badge tabs
```

New files under `components/ui/`.

---

## 8. Frontend: App Layout + Routing

**Create:** `frontend/src/components/AppLayout.tsx`

- Sidebar: app logo, "Trials" link, trial list
- Top bar: user avatar + logout
- Main content area
- Responsive collapse on mobile

**Modify:** `frontend/src/App.tsx`

| Route | Component |
|---|---|
| `/` | Redirect to `/trials` |
| `/trials` | `TrialsListPage` |
| `/trials/:id` | `TrialDetailPage` |

---

## 9. Frontend: Trials Pages

**`frontend/src/pages/TrialsListPage.tsx`:**
- Fetch `GET /api/trials`
- Grid of trial cards (name, description, member count, date)
- "Create Trial" button → `CreateTrialDialog`
- Empty state

**`frontend/src/pages/TrialDetailPage.tsx`:**
- Fetch `GET /api/trials/:id`
- Tabs: Documents | Members | Settings

---

## 10. Frontend: Document Upload + List

- **`components/UploadDialog.tsx`**: drag-and-drop zone, file validation (PDF only, <50MB), upload via `fetch`, poll document status after upload.
- **`components/DocumentsList.tsx`**: table with filename, status badge (colored), date, delete button. Poll for status updates on non-terminal statuses.
- **`components/MembersList.tsx`**: member list with avatars, invite dialog, remove button (admin only).

---

## Execution Order

1. DB models + Alembic migration
2. Qdrant client + collection setup
3. shadcn UI components (frontend prep)
4. Frontend layout + routing skeleton
5. Trials API (CRUD + members)
6. Frontend trials list + detail pages
7. Frontend members UI
8. Ingestion pipeline (parser → chunker → embedder → pipeline)
9. Document upload API + BackgroundTasks wiring
10. Document deletion API
11. Frontend document upload/list/delete UI
12. Integration testing
13. **DELETE THIS FILE**
