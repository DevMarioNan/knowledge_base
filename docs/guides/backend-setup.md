# Backend setup

This project uses a Python + FastAPI backend because the server is responsible for AI and document-processing work — ingestion, chunking, embeddings, retrieval, reranking, and evaluation. Keeping this logic behind a dedicated API keeps the frontend focused on the user experience while the backend owns data access, orchestration, and grounding.

## Init (from empty `backend/`)

```bash
cd backend
uv sync
uv add fastapi uvicorn pydantic pydantic-settings httpx structlog openai cohere qdrant-client sqlalchemy alembic "psycopg[binary]" ragas
uv add --dev pytest ruff pytest-asyncio
```

If using Pinecone instead of Qdrant:

```bash
uv add pinecone
```

## Database migrations

Alembic owns PostgreSQL schema changes. SQLAlchemy models describe the app tables, and Alembic migrations apply those changes.

Initialize Alembic from `backend/`:

```bash
uv run alembic init alembic
```

Configure `alembic/env.py` to import the app's SQLAlchemy metadata and read the direct database URL from `app.config.settings`.

Create a migration after changing SQLAlchemy models:

```bash
uv run alembic revision --autogenerate -m "add document tables"
```

Apply migrations:

```bash
uv run alembic upgrade head
```

## Vector DB setup

Qdrant collections and indexes are defined in `app/vector_db/setup.py` and initialized in a FastAPI startup hook. Do not create collections manually in the Qdrant dashboard.

The setup script must define:

- Collection name
- Embedding dimensions (matching the model in `config.py`)
- Distance metric (cosine)
- Payload schema for metadata (document_id, page_number, source_filename, chunk_text)

## Run

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

## Imports (`from app...`)

`backend/app` is installed as an editable package by `uv sync`, so `from app...` imports work from uvicorn, direct Python execution, and tests.

The `[build-system]` and `[tool.hatch.build.targets.wheel]` sections in `backend/pyproject.toml` tell uv how to install the local `app/` package. Without that package install, imports depend on the current working directory or a manually configured `PYTHONPATH`.

Preferred API server command:

```bash
cd backend
uv run uvicorn app.main:app --reload
```

Direct file execution also works:

```bash
cd backend
uv run python app/main.py
```

## Docker

For local development with all services:

```bash
docker compose up -d   # starts PostgreSQL + Qdrant
cd backend && uv run uvicorn app.main:app --reload
```

For production-like builds:

```bash
docker compose up --build
```
