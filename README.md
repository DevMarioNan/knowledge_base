<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://img.shields.io/badge/TrialBase-Clinical%20RAG-2563eb?style=for-the-badge&logo=openai&logoColor=white">
  <img alt="TrialBase" src="https://img.shields.io/badge/TrialBase-Clinical%20RAG-2563eb?style=for-the-badge&logo=openai&logoColor=white">
</picture>

<p align="center">
  <strong>Grounded Question-Answering over Clinical Trial Documents</strong>
  <br>
  <em>A production-grade RAG system for clinical research organizations</em>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#project-structure">Project Structure</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#development">Development</a> •
  <a href="#deployment">Deployment</a> •
  <a href="#evaluation">Evaluation</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-2563eb?style=flat&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/TypeScript-6.0-3178C6?style=flat&logo=typescript&logoColor=white">
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white">
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white">
  <img src="https://img.shields.io/badge/Qdrant-1.13-000000?style=flat&logo=qdrant&logoColor=white">
</p>

---

## Overview

**TrialBase** is a Retrieval-Augmented Generation (RAG) system built for clinical research organizations. It ingests clinical trial documents (protocols, consent forms, safety reports, etc.), indexes them via hybrid search (dense vectors + BM25 keyword), reranks results with Cohere, and generates grounded answers with mandatory citations.

Designed for **Lumina Clinical Research** — a mid-sized CRO where staff spend ~50% of their time cross-referencing documents — TrialBase eliminates manual lookups while guaranteeing that every answer is traceable to its source.

### Problem

- Clinical staff spend hours searching through PDFs for specific data points
- Answers must be strictly grounded in source documents — hallucination is unacceptable
- No visibility into whether the RAG pipeline is producing accurate results

### Solution

- **Hybrid retrieval** — dense embeddings + BM25 keyword search fused via RRF
- **Cohere reranking** — top results reordered by semantic relevance
- **Grounded generation** — LLM constrained to provided context with mandatory `[n]` citations
- **Evaluation dashboard** — RAGAS metrics (faithfulness, relevancy, precision, recall) tracked over time

---

## Features

### Core RAG

| Feature | Description |
|---|---|
| **PDF Ingestion** | Async pipeline: upload → parse (PyMuPDF/pdfminer) → hybrid chunk → embed → store |
| **Hybrid Search** | Dense vectors (OpenAI `text-embedding-3-small`) + BM25 keyword search fused via RRF |
| **Contextual Reranking** | Cohere rerank on top-K results before passing to the LLM |
| **Grounded Generation** | GPT-4o / GPT-4o-mini with strict context-only instruction |
| **Citations** | Every claim tagged with `[n]` — tooltip shows source excerpt, page, document |
| **Grounding Guardrails** | LLM instructed to say "I don't know" when context lacks the answer |

### Collaboration

| Feature | Description |
|---|---|
| **Trials** | Isolated workspaces for each clinical trial or study |
| **Team Members** | Invite users per trial with admin/member roles |
| **Chat Threads** | Persistent conversations per trial with history |

### Evaluation

| Feature | Description |
|---|---|
| **Datasets** | Create Q&A datasets with ground-truth answers per trial |
| **RAGAS Metrics** | Faithfulness, answer relevancy, context precision, context recall |
| **Run History** | Track pipeline performance over time with visual charts |
| **Threshold Alerts** | Configurable evaluation thresholds per trial |

### Operations

| Feature | Description |
|---|---|
| **Dockerized** | One command to spin up Postgres, Qdrant, backend, and frontend |
| **Async First** | Non-blocking ingestion pipeline with background task processing |
| **JWT Auth** | Register, login, and token-refresh flow |
| **SSE Streaming** | Real-time token streaming from LLM to UI |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React SPA)                  │
│  Vite + TypeScript + Tailwind CSS + shadcn/ui               │
│  Nginx reverse-proxies /api → backend                       │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / SSE
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                         │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │  Auth    │  │  Trials  │  │  Chat    │  │  Evaluation   │ │
│  │  (JWT)   │  │  CRUD    │  │  SSE     │  │  (RAGAS)      │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │  Ingestion   │  │  Retrieval   │  │  LLM / Prompts     │ │
│  │  Pipeline    │  │  Hybrid+RRF  │  │  OpenAI + Context  │ │
│  └──────────────┘  └──────┬───────┘  └────────────────────┘ │
│                           │                                  │
└───────────────────────────┼──────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│  PostgreSQL  │  │    Qdrant    │  │  OpenAI / Cohere  │
│  (metadata,  │  │  (vectors,   │  │  (embeddings,     │
│   users,     │  │   BM25)      │  │   completion,     │
│   docs,      │  │              │  │   rerank)         │
│   runs)      │  │              │  │                   │
└──────────────┘  └──────────────┘  └──────────────────┘
```

### Retrieval Pipeline

```
User Query
    │
    ▼
┌─────────────────────┐
│  Dense Search (Qdrant) │  ← OpenAI embedding
│  + BM25 (Qdrant)      │
└──────────┬──────────┘
           │ RRF Fusion (top-K)
           ▼
┌─────────────────────┐
│  Cohere Rerank      │  ← top-N most relevant
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  LLM Generation     │  ← GPT-4o with context + citations
└─────────────────────┘
```

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- API keys: [OpenAI](https://platform.openai.com/api-keys), [Cohere](https://dashboard.cohere.com/api-keys)

### 1. Clone & Configure

```bash
git clone https://github.com/DevMarioNan/knowledge_base.git
cd knowledge_base
cp .env.example.docker .env
```

Edit `.env` and set your API keys:

```env
JWT_SECRET=your-secret-key-change-in-production
OPENAI_API_KEY=sk-...
COHERE_API_KEY=...
```

### 2. Launch

```bash
docker compose up -d
```

This starts:
- **PostgreSQL 16** — relational data store
- **Qdrant** — vector database (dense + BM25 indexes)
- **Backend** — FastAPI on port 8000
- **Frontend** — Vite SPA via nginx on port 80

### 3. Open

Navigate to [http://localhost](http://localhost). Register an account, create a trial, upload PDFs, and start asking questions.

---

## Project Structure

```
knowledge_base/
├── backend/                          # FastAPI service
│   ├── app/
│   │   ├── api/                      # Route handlers
│   │   │   ├── auth.py               #   /api/auth/*
│   │   │   ├── trials.py             #   /api/trials/*
│   │   │   ├── documents.py          #   /api/documents/*
│   │   │   ├── chat.py               #   /api/chat/* (SSE)
│   │   │   └── evaluation.py         #   /api/evaluation/*
│   │   ├── auth/                     # JWT + password utilities
│   │   ├── chat/                     # Chat orchestration, streaming, citations
│   │   ├── database/                 # SQLAlchemy models + async session
│   │   ├── evaluation/               # RAGAS integration
│   │   ├── ingestion/                # PDF parsing, chunking, embedding
│   │   ├── llm/                      # OpenAI client + token management
│   │   ├── prompts/                  # System prompt + context builder
│   │   ├── retrieval/                # Hybrid search, reranker
│   │   └── vector_db/                # Qdrant client + collection setup
│   ├── alembic/                      # Database migrations
│   ├── scripts/                      # E2E test, sample PDF generator
│   ├── tests/                        # Pytest suite
│   └── Dockerfile
│
├── frontend/                         # React SPA
│   ├── src/
│   │   ├── components/               # UI components + shadcn primitives
│   │   ├── pages/                    # Route pages
│   │   ├── hooks/                    # useChat (SSE streaming)
│   │   ├── lib/                      # API client, auth context, env, utils
│   │   ├── App.tsx                   # Router setup
│   │   └── main.tsx                  # Entry point
│   ├── nginx.conf                    # SPA → API reverse proxy
│   └── Dockerfile
│
├── docs/                             # Architecture, plan, guides
├── docker-compose.yml                # All services
├── AGENTS.md                         # Agent/IDE instructions
└── README.md
```

---

## Configuration

All configuration is driven by environment variables through a single settings module (`backend/app/config.py`).

### Required

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (default: `postgresql+asyncpg://postgres:postgres@postgres:5432/trialbase`) |
| `OPENAI_API_KEY` | OpenAI API key |
| `COHERE_API_KEY` | Cohere API key |
| `JWT_SECRET` | Secret key for JWT token signing |

### Optional

| Variable | Default | Description |
|---|---|---|
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant gRPC endpoint |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI chat model |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `CHUNK_SIZE` | `800` | Target tokens per chunk |
| `CHUNK_OVERLAP` | `160` | Token overlap between chunks |
| `TOP_K_RETRIEVAL` | `20` | Candidates from hybrid search |
| `TOP_N_RERANK` | `10` | Passed to LLM after reranking |
| `COHERE_RERANK_MODEL` | `rerank-v3.5` | Cohere rerank model |

---

## Development

### Backend

```bash
cd backend
uv sync                        # Install dependencies
cp .env.example .env           # Configure environment
uv run alembic upgrade head    # Run migrations
uv run uvicorn app.main:app --reload  # Start dev server
```

### Frontend

```bash
cd frontend
pnpm install                   # Install dependencies
cp .env.example .env           # VITE_API_BASE_URL=http://localhost:8000/api
pnpm dev                       # Start Vite dev server (port 5173)
```

### Database Migrations

```bash
cd backend
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

### Testing

```bash
cd backend
uv run pytest                          # Unit tests
uv run python scripts/e2e_test.py      # End-to-end test
uv run python scripts/generate_sample_pdfs.py  # Generate sample documents
```

### Code Quality

```bash
cd backend
uv run ruff check .
uv run ruff format --check .

cd frontend
pnpm tsc --noEmit
```

---

## API Overview

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Create account |
| `POST` | `/api/auth/login` | Get JWT tokens |
| `GET` | `/api/auth/me` | Current user |
| `POST` | `/api/auth/refresh` | Refresh access token |
| `GET` | `/api/trials` | List trials |
| `POST` | `/api/trials` | Create trial |
| `GET` | `/api/trials/{id}` | Trial detail |
| `POST` | `/api/trials/{id}/documents` | Upload document(s) |
| `GET` | `/api/trials/{id}/documents` | List documents |
| `DELETE` | `/api/documents/{id}` | Delete document |
| `POST` | `/api/trials/{id}/chat` | Ask question (SSE stream) |
| `GET` | `/api/trials/{id}/threads` | Chat threads |
| `GET` | `/api/trials/{id}/evaluation/datasets` | Evaluation datasets |
| `POST` | `/api/trials/{id}/evaluation/runs` | Start evaluation run |

---

## Evaluation

TrialBase uses [RAGAS](https://docs.ragas.io/) to evaluate pipeline quality. Each evaluation run computes four metrics:

| Metric | What it measures |
|---|---|
| **Faithfulness** | Is the answer factually consistent with the retrieved context? |
| **Answer Relevancy** | How relevant is the answer to the question? |
| **Context Precision** | Are all retrieved chunks actually relevant? |
| **Context Recall** | Can the ground truth be attributed to the context? |

Create a dataset of question-answer pairs per trial, then run evaluations from the dashboard to track performance over time.

---

## Deployment

### Production Build

```bash
docker compose -f docker-compose.yml up -d --build
```

### Environment Variables

Set production values in `.env`:

```env
JWT_SECRET=<random-256-bit-key>
OPENAI_API_KEY=sk-...
COHERE_API_KEY=...
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/trialbase
```

### Health Checks

- Backend: `GET /docs` (Swagger UI)
- Frontend: `GET /` (returns SPA)

---

## Tech Stack

### Backend

| Technology | Purpose |
|---|---|
| **Python 3.12+** | Runtime |
| **FastAPI** | Web framework (async) |
| **SQLAlchemy 2.0** | ORM (async) |
| **PostgreSQL 16** | Relational database |
| **Alembic** | Migrations |
| **Qdrant** | Vector database (dense + BM25) |
| **OpenAI SDK** | Embeddings + Chat Completions |
| **Cohere SDK** | Semantic reranking |
| **RAGAS** | Evaluation metrics |
| **PyMuPDF / pdfminer** | PDF parsing |

### Frontend

| Technology | Purpose |
|---|---|
| **React 19** | UI framework |
| **TypeScript 6** | Type safety |
| **Vite 8** | Build tool |
| **Tailwind CSS 4** | Styling |
| **shadcn/ui** | Component library (Radix primitives) |
| **react-markdown + remark-gfm** | LLM markdown rendering |
| **recharts** | Evaluation charts |
| **React Router** | Client-side routing |

### Infrastructure

| Technology | Purpose |
|---|---|
| **Docker Compose** | Local orchestration |
| **nginx** | SPA serving + API proxy |

---

## Domain Model

- **Trial** — An isolated workspace representing a clinical trial or study
- **Document** — A PDF uploaded to a trial, processed through the ingestion pipeline
- **DocumentChunk** — A piece of a document stored as a vector in Qdrant
- **ChatThread** — A conversation within a trial
- **ChatMessage** — A question or answer in a thread
- **MessageCitation** — Links each answer claim back to its source chunk
- **EvaluationDataset** — A set of Q&A pairs for measuring pipeline quality
- **EvaluationRun** — A snapshot of RAGAS metrics for a dataset

See [CONTEXT.md](./CONTEXT.md) for the full ubiquitous language glossary.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

### Commit Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — new feature
- `fix:` — bug fix
- `chore:` — maintenance
- `docs:` — documentation
- `refactor:` — code restructuring

### Code Standards

- **Python:** Ruff linting, type annotations, async-first
- **TypeScript:** Strict mode, no `any`, no `axios` (use native `fetch`)
- **CSS:** Tailwind utility classes, no custom CSS unless necessary
- **Dependencies:** Write it yourself unless the alternative would be non-trivial or error-prone

---

## License

MIT

---

<p align="center">
  Built with ❤️ for Lumina Clinical Research
</p>
