# Backend — agent notes

This is the FastAPI service for the RAG Knowledge Base App. Read [../AGENTS.md](../AGENTS.md) first — universal building rules live there. This file adds backend-specific conventions.

## Stack

- Python 3.12+
- FastAPI + uvicorn
- Pydantic v2 + pydantic-settings
- `httpx` for outbound HTTP
- `pytest` for tests
- SQLAlchemy (async with `asyncpg`) + Alembic migrations for relational schema (users, documents, evaluations)
- Qdrant Python client (or Pinecone client) for vector storage
- OpenAI SDK for LLM & embeddings
- Cohere SDK for re-ranking
- RAGAS for evaluation metrics
- `structlog` for logging
- `uv` for dependency + project management

## Dependency policy

See universal policy in [../AGENTS.md](../AGENTS.md). Backend-specific:

- **Prefer stdlib:** `pathlib`, `datetime`, `uuid`, `enum`, `dataclasses`, `asyncio`, `collections`, `itertools`, `json`, `urllib`.
- **Not OK without justification:** `python-dateutil`, `toolz`, `funcy`, `more-itertools`, small JSON/string micro-libs, "ergonomic" wrappers on top of declared SDKs.
- Heavy RAG frameworks (like LangChain or LlamaIndex) are **not allowed** unless explicitly approved. We want transparent, easily debuggable Python code for our retrieval and ingestion pipelines.
- Dev deps (test/lint/build) have a looser bar but still pick widely-used, low-footprint tools (`pytest`, `ruff`, `httpx`).

## Layout (to be created during build)

```text
backend/
├── alembic/
│   ├── env.py           # Imports app database metadata for autogenerate
│   └── versions/        # Reviewed migration files
├── alembic.ini
├── app/
│   ├── main.py          # FastAPI entrypoint
│   ├── config.py        # Pydantic settings — single source of truth for env
│   ├── api/             # FastAPI routers (chat, ingest, auth, evaluation)
│   ├── auth/            # JWT verification + current user dependency
│   ├── chat/            # Turn orchestration, prompt building, streaming
│   ├── ingestion/       # Document parsing, chunking, embedding generation, background tasks
│   ├── retrieval/       # Hybrid search (Vector + Keyword), RRF fusion, Cohere re-ranking
│   ├── evaluation/      # RAGAS dataset generation, metric computation, dashboard data APIs
│   ├── database/        # SQLAlchemy models, session management, typed query helpers
│   ├── vector_db/       # Qdrant/Pinecone client wrappers, collection management
│   ├── llm/             # OpenAI/Cohere client wrappers, retry logic, token counting
│   └── prompts/         # Prompt/instruction templates
├── scripts/             # One-off utility scripts (e.g., backfill embeddings, seed data)
├── tests/
└── pyproject.toml
```

## Code style (backend-specific)

- **Type hints on public functions and module-level things.** Don't annotate every local.
- **Async by default in request-path code.** Don't run blocking I/O on the event loop. 
- **Background processing for heavy work:** Document parsing (e.g., PDF text extraction) and bulk embedding generation are CPU/IO intensive. They **must** run in background tasks (e.g., FastAPI `BackgroundTasks` or a task queue) to avoid blocking the event loop. Never do heavy CPU-bound work directly in an async route handler.
- **Use `async def` for all route handlers** and any I/O service function.
- **Validate at boundaries only.** HTTP input is validated by Pydantic models. External API responses (Qdrant, OpenAI, Cohere) are validated when parsed. Internal callers are trusted.

## Configuration

- `app.config.settings` is the single source of truth. Import settings where needed; never call `os.getenv` in app code, never call `load_dotenv`.
- If a third-party SDK reads `os.environ` directly, add the mirror in `config.py` — don't sprinkle `setdefault` elsewhere.
- Fail fast on startup when required env vars are missing (e.g., `OPENAI_API_KEY`, `COHERE_API_KEY`, `QDRANT_URL` / `PINECONE_API_KEY`, `DATABASE_URL`).

## Database & Vector DB management

- **Postgres:** Alembic is the source of truth for relational schema changes. Do not change production tables manually in a DB client. SQLAlchemy models describe normal tables and columns. Alembic autogenerate creates candidate migrations, but every generated migration must be reviewed before applying.
- **Vector DB (Qdrant/Pinecone):** Collections and indexes must be defined and initialized via code (e.g., in a startup hook or `app/vector_db/setup.py`). Do not create collections manually in the Qdrant/Pinecone dashboard.
- Embedding dimensions, distance metrics, and payload schemas must be explicitly defined in the vector DB setup code and strictly match the embedding model configured in `config.py`.
- Run relational migrations from `backend/` with `uv run alembic upgrade head`.

## Tests

- **Prefer unit over integration.** Mock at the service boundary (mock OpenAI, Cohere, and Qdrant clients).
- Fast suite (`pytest -m "not integration"`) must stay green and hit no network / no DB.
- Integration tests go behind `@pytest.mark.integration` and may require live API credentials.
- Tests live next to what they test (`retrieval/fusion.py` → `tests/retrieval/test_fusion.py`).
- Required test coverage: document chunking logic, Reciprocal Rank Fusion (RRF) math, Cohere re-ranking payload formatting, RAGAS metric mocking.

## Anti-patterns (rejected)

- `os.getenv` / `load_dotenv` in modules.
- Wrapping FastAPI responses in custom envelope classes.
- Over-catching `Exception` just to log and re-raise; let it propagate.
- Shared state through globals instead of FastAPI `app.state` or DI.
- Silent fallbacks that hide real config errors.
- Running document parsing or bulk embedding synchronously in the request-response cycle.
- Hardcoding vector dimensions, collection names, or model names in retrieval logic instead of pulling from `settings`.
- Mocking the LLM in unit tests without also testing the grounding/citation contract — the prompt and citation extraction are the product.
