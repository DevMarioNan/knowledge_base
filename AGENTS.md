# Agent Instructions

This file is the source of truth for any coding agent (Claude Code, Cursor, Codex, etc.) working in this repo. Read it before touching code.

## Stack

- **Backend:** Python + FastAPI
- **Frontend:** Vite + React SPA + TypeScript + Tailwind + Shadcn UI
- **Database:** PostgreSQL (users, documents, evaluations) + SQLAlchemy / Alembic
- **Vector Database:** Qdrant (self-hosted via Docker) or Pinecone
- **Retrieval:** Hybrid search (Vector + Keyword) + Cohere Rerank
- **Evaluation:** RAGAS
- **LLM + embeddings:** OpenAI (Chat Completions + Embeddings)
- **Hosting/Deployment:** Docker + Docker Compose

Stack is locked unless explicitly changed. Don't propose alternatives without a stated reason.

## Repo layout

```text
rag-knowledge-base/
├── AGENTS.md           # this file
├── README.md
├── docker-compose.yml  # local services (Postgres, Qdrant)
├── docs/               # specs, briefs, design notes
├── backend/            # FastAPI service (see backend/AGENTS.md)
└── frontend/           # React SPA (see frontend/AGENTS.md)
```

## RAG System Guidelines

### Ingestion & Chunking
- Documents uploaded by users must be processed asynchronously. Do not block the main thread during PDF parsing or embedding generation.
- Chunking strategy must be clearly defined in the configuration (e.g., recursive character splitting with overlap). Respect semantic boundaries (paragraphs, headers) where possible.
- Metadata (document ID, page number, source filename) must be attached to every vector in Qdrant/Pinecone and stored in the relational DB for citation tracking.

### Retrieval & Re-ranking
- **Hybrid Search:** Fetch top-K candidates using both dense vectors (OpenAI embeddings) and sparse vectors/keyword matching (BM25).
- **Re-ranking:** ALWAYS pass the top-K retrieved chunks through Cohere Rerank before passing context to the LLM. Reranking drastically improves faithfulness and context precision.
- **Context Window:** Be mindful of the LLM's context window. Re-ranking allows us to send only the most relevant top-N chunks to the prompt.

### Citations & Generation
- The LLM must be prompted to ground its answers strictly in the provided context. 
- **Citations are mandatory.** The system must return the exact chunk IDs or document references used to generate each claim. The frontend must be able to map these IDs back to the UI components to show source tooltips/highlights.
- If the context does not contain the answer, the LLM must be instructed to say "I don't know based on the provided documents" rather than hallucinating.

### Evaluation Dashboard
- **RAGAS:** Use RAGAS to evaluate the RAG pipeline. Core metrics to compute: `faithfulness`, `answer_relevancy`, `context_precision`, and `context_recall`.
- Evaluation runs should be reproducible and stored in the database to track pipeline performance over time on the evaluation dashboard.

## Dependency policy

**Default: write it yourself. Reach for a library only when the alternative would be non-trivial, error-prone, or reinvention of a standard.** Every dependency is a liability — bundle size, supply-chain risk, future upgrade work.

OK to depend on:

- Things that are genuinely hard to get right (HTTP clients, ASGI servers, SQL drivers, parsers, LLM SDKs, ORM, migrations, auth SDKs).
- The declared stack (FastAPI, React, Tailwind, Qdrant/Pinecone clients, Cohere, RAGAS, OpenAI SDK, SQLAlchemy, etc.).

Not OK:

- Helper libraries that wrap 5–20 lines of stdlib or platform APIs.
- Frameworks where a function would do.
- "Nicer API" layers on top of an already-present dependency (e.g., heavy LangChain/LlamaIndex abstractions if simple Python scripts suffice for your specific ingestion pipeline).

Before adding a runtime dep, answer in the commit message:

1. What exactly does it do that we can't write in <30 lines of clear code?
2. How often does it get used?
3. What's its maintenance / transitive-dep footprint?

Per-stack specifics live in `backend/AGENTS.md` and `frontend/AGENTS.md`.

## Configuration

A single settings module is the source of truth for environment per service (`backend/app/config.py`, `frontend/lib/env.ts`). Do not call `os.getenv` / read `process.env` directly in app code. Do not call `load_dotenv` anywhere. If a third-party SDK reads env vars directly, mirror them in the settings module — don't sprinkle `setdefault` elsewhere.

Fail fast on startup if required config is missing (e.g., OpenAI API keys, Cohere API keys, Qdrant/Pinecone URLs). No silent fallbacks that hide real config errors.

## Code style (universal)

- **Small, obvious functions.** A 15-line function with clear names beats a three-class abstraction.
- **No premature abstraction.** Three similar lines is better than a badly-named base class. Extract when there's a third caller, not a hypothetical one.
- **No error handling for cases that can't happen.** Trust internal callers and framework guarantees. Validate only at boundaries: HTTP input, external APIs (OpenAI, Cohere, Vector DBs), DB writes, untrusted parsing.
- **No backwards-compat shims** unless explicitly asked for.
- **No feature flags** added speculatively.
- **Comments:** explain *why* when non-obvious, never *what*. Remove stale TODOs.
- **Keep files focused.** Prefer small modules.
