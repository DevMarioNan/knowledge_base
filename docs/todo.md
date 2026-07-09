# TrialBase — Implementation Todo

## Phase 1 — Foundation

- [x] Scaffold backend: FastAPI app, `config.py`, `structlog`, project layout per `backend/AGENTS.md`
- [x] Scaffold frontend: Vite + React + TypeScript + Tailwind + shadcn/ui per `frontend/AGENTS.md`
- [x] Set up Docker Compose (PostgreSQL + Qdrant)
- [x] Create `.env.example` for backend (DATABASE_URL, SECRET_KEY, OPENAI_API_KEY, COHERE_API_KEY, QDRANT_URL, etc.)
- [x] Create `.env.example` for frontend (VITE_API_URL, etc.)
- [x] SQLAlchemy models: `users`, `trials`, `trial_members` + Alembic migration setup
- [x] Backend auth: registration (email domain validation), login, JWT issuance, current-user dependency
- [x] Frontend: shared API client (`lib/http.ts`, `lib/api.ts`), auth context, login/signup pages
- [x] Protected routes on frontend, JWT refresh flow

## Phase 2 — Trials & Document Ingestion

- [x] Trials CRUD: create trial, list user's trials, trial detail page
- [x] Trial membership: invite by email, member list, remove member
- [x] Document upload endpoint + frontend upload UI with progress indicator
- [x] Ingestion pipeline: PDF parsing (structure-aware + fallback), chunking, embedding generation
- [x] Async background processing for ingestion (FastAPI `BackgroundTasks`)
- [x] Qdrant collection setup + chunk storage with metadata payload
- [x] Document lifecycle status tracking (`uploaded → parsing → chunking → embedding → ready / failed`)
- [x] Document deletion (soft delete + Qdrant chunk removal)

## Phase 3 — Retrieval & Generation (Core RAG)

- [x] Hybrid retrieval: dense vector search + Qdrant full-text (BM25) + RRF fusion
  - Note: BM25 uses local pure-Python computation (scrolls all points), not Qdrant's built-in full-text search API. TEXT payload index is created but unused. Works for moderate collections.
- [x] Cohere reranking integration
- [x] Prompt construction: grounding instructions, citation format, context window management
  - Note: context window management now active — `build_messages` drops lowest-scored chunks if token count exceeds model limit.
- [x] Chat streaming endpoint (SSE): retrieve → rerank → generate → stream
- [x] Citation parsing and validation (every `[n]` maps to a retrieved chunk)
- [x] Grounding failure detection and structured `grounding_failure` SSE event
- [x] Thread CRUD: auto-create on first message, auto-generate title, list threads per trial
  - Note: No `DELETE`/`PUT` endpoints for threads. Explicit thread create uses static "New Chat" title (only auto-generated after first message).
- [x] Chat messages persistence: user message, assistant message, `message_citations`
- [x] Frontend: chat UI with streaming, citation tooltips, source passage panel, grounding failure UI

## Phase 4 — Evaluation Dashboard

- [x] Evaluation dataset CRUD: add/edit/delete question + ground-truth answer pairs per trial
- [x] Evaluation run execution: process dataset through full pipeline, compute RAGAS metrics
- [x] Evaluation results storage: per-run and per-question scores
- [x] Evaluation dashboard UI: metric tables, trend charts over time, per-question drill-down
- [x] "Last evaluated" indicator on trials

## Phase 5 — Polish & Production Readiness

- [ ] Error handling: friendly error messages, network vs. HTTP distinction in frontend
- [ ] Empty states and loading states across all pages
- [ ] LLM output sanitization (DOMPurify) in chat rendering
- [ ] Document status polling / real-time updates in frontend
- [ ] Configuration validation: fail-fast on missing env vars
- [ ] End-to-end manual testing with sample clinical trial documents
- [ ] Docker Compose production build configuration

## Chat UI Improvements

- [ ] Auto-scroll chat to bottom on each new message
- [ ] Improve citation view — better visual display of sources
- [ ] Render model responses as Markdown instead of plain text
