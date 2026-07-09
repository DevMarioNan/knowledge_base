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

- [ ] Trials CRUD: create trial, list user's trials, trial detail page
- [ ] Trial membership: invite by email, member list, remove member
- [ ] Document upload endpoint + frontend upload UI with progress indicator
- [ ] Ingestion pipeline: PDF parsing (structure-aware + fallback), chunking, embedding generation
- [ ] Async background processing for ingestion (FastAPI `BackgroundTasks`)
- [ ] Qdrant collection setup + chunk storage with metadata payload
- [ ] Document lifecycle status tracking (`uploaded → parsing → chunking → embedding → ready / failed`)
- [ ] Document deletion (soft delete + Qdrant chunk removal)

## Phase 3 — Retrieval & Generation (Core RAG)

- [ ] Hybrid retrieval: dense vector search + Qdrant full-text (BM25) + RRF fusion
- [ ] Cohere reranking integration
- [ ] Prompt construction: grounding instructions, citation format, context window management
- [ ] Chat streaming endpoint (SSE): retrieve → rerank → generate → stream
- [ ] Citation parsing and validation (every `[n]` maps to a retrieved chunk)
- [ ] Grounding failure detection and structured `grounding_failure` SSE event
- [ ] Thread CRUD: auto-create on first message, auto-generate title, list threads per trial
- [ ] Chat messages persistence: user message, assistant message, `message_citations`
- [ ] Frontend: chat UI with streaming, citation tooltips, source passage panel, grounding failure UI

## Phase 4 — Evaluation Dashboard

- [ ] Evaluation dataset CRUD: add/edit/delete question + ground-truth answer pairs per trial
- [ ] Evaluation run execution: process dataset through full pipeline, compute RAGAS metrics
- [ ] Evaluation results storage: per-run and per-question scores
- [ ] Evaluation dashboard UI: metric tables, trend charts over time, per-question drill-down
- [ ] "Last evaluated" indicator on trials

## Phase 5 — Polish & Production Readiness

- [ ] Error handling: friendly error messages, network vs. HTTP distinction in frontend
- [ ] Empty states and loading states across all pages
- [ ] LLM output sanitization (DOMPurify) in chat rendering
- [ ] Document status polling / real-time updates in frontend
- [ ] Configuration validation: fail-fast on missing env vars
- [ ] End-to-end manual testing with sample clinical trial documents
- [ ] Docker Compose production build configuration
