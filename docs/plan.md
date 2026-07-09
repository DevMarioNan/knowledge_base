# TrialBase — Implementation Plan

## Domain Decisions

| Decision | Resolution |
|---|---|
| Postgres hosting | Supabase (hosted Postgres only, no Supabase Auth) |
| Auth | FastAPI-issued JWTs, email/password |
| Registration | Self-service, `@luminaclinical.com` only |
| User roles | Single role — all users upload and ask questions |
| Trials | First-class entity, created by any user |
| Trial access | Explicit membership, invite by email, any member can invite |
| Thread visibility | All trial members see all threads, user attribution on messages |
| Thread creation | Auto-create on first message, auto-generate title |
| Document formats | PDF only |
| Document lifecycle | `uploaded → parsing → chunking → embedding → ready` (+ `failed`) |
| Document deletion | Soft delete, chunks removed from Qdrant, messages/citations preserved |
| Chunking strategy | Hybrid: structure-aware (PDF bookmarks/headers) with recursive character fallback |
| Keyword search | Qdrant built-in full-text search (BM25) |
| Citations | Inline `[n]` markers + structured source list |
| Grounding failure | Distinct UI + "upload more documents" suggestion |
| Evaluation datasets | Trial-scoped, created in-app |
| Evaluation runs | Manual trigger |

---

## Phase 1 — Foundation

Scaffold both services, set up infrastructure, and get auth working end-to-end.

1. Scaffold backend: FastAPI app, `config.py`, `structlog`, project layout per `backend/AGENTS.md`
2. Scaffold frontend: Vite + React + TypeScript + Tailwind + shadcn/ui per `frontend/AGENTS.md`
3. Set up Docker Compose (Qdrant + local Postgres for dev; prod connects to Supabase)
4. SQLAlchemy models: `users`, `trials`, `trial_members` + Alembic migration setup
5. Backend auth: registration (email domain validation), login, JWT issuance, current-user dependency
6. Frontend: shared API client (`lib/http.ts`, `lib/api.ts`), auth context, login/signup pages
7. Protected routes on frontend, JWT refresh flow

**Deliverable:** User can sign up, log in, and see an empty app.

---

## Phase 2 — Trials & Document Ingestion

Users can create trials, manage membership, and upload documents that get processed into searchable chunks.

8. Trials CRUD: create trial, list user's trials, trial detail page
9. Trial membership: invite by email, member list, remove member
10. Document upload endpoint + frontend upload UI with progress indicator
11. Ingestion pipeline: PDF parsing (structure-aware + fallback), chunking, embedding generation
12. Async background processing for ingestion (FastAPI `BackgroundTasks`)
13. Qdrant collection setup + chunk storage with metadata payload
14. Document lifecycle status tracking (`uploaded → parsing → chunking → embedding → ready / failed`)
15. Document deletion (soft delete + Qdrant chunk removal)

**Deliverable:** User can create a trial, invite colleagues, upload PDFs, and see them reach "ready" status.

---

## Phase 3 — Retrieval & Generation (Core RAG)

The actual question-answering pipeline — hybrid search, reranking, grounded generation with citations.

16. Hybrid retrieval: dense vector search + Qdrant full-text (BM25) + RRF fusion
17. Cohere reranking integration
18. Prompt construction: grounding instructions, citation format, context window management
19. Chat streaming endpoint (SSE): retrieve → rerank → generate → stream
20. Citation parsing and validation (every `[n]` maps to a retrieved chunk)
21. Grounding failure detection and structured `grounding_failure` SSE event
22. Thread CRUD: auto-create on first message, auto-generate title, list threads per trial
23. Chat messages persistence: user message, assistant message, `message_citations`
24. Frontend: chat UI with streaming, citation tooltips, source passage panel, grounding failure UI

**Deliverable:** User can ask questions in a trial, get sourced answers with clickable citations, and see "I don't know" when context is insufficient.

---

## Phase 4 — Evaluation Dashboard

Prove the system works before it touches a live trial.

25. Evaluation dataset CRUD: add/edit/delete question + ground-truth answer pairs per trial
26. Evaluation run execution: process dataset through full pipeline, compute RAGAS metrics
27. Evaluation results storage: per-run and per-question scores
28. Evaluation dashboard UI: metric tables, trend charts over time, per-question drill-down
29. "Last evaluated" indicator on trials

**Deliverable:** Medical monitors can build a Q&A dataset, run evaluation, and see faithfulness/precision/recall/relevancy scores.

---

## Phase 5 — Polish & Production Readiness

Harden the system for Lumina's pilot.

30. Error handling: friendly error messages, network vs. HTTP distinction in frontend
31. Empty states and loading states across all pages
32. LLM output sanitization (DOMPurify) in chat rendering
33. Document status polling / real-time updates in frontend
34. Configuration validation: fail-fast on missing env vars
35. End-to-end manual testing with sample clinical trial documents
36. Docker Compose production build configuration

**Deliverable:** Pilot-ready TrialBase for Lumina's Head of Clinical Operations.
