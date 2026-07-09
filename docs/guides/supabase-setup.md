# Supabase setup

We use Supabase for **PostgreSQL** (users, trials, documents, evaluations) only. Auth is handled by the FastAPI backend directly (email/password, JWT). Qdrant (self-hosted via Docker) handles vector storage — see step 5.

## 1. Create an account

1. Go to [supabase.com](https://supabase.com) and sign up (GitHub or email).
2. Confirm your email if prompted.
3. You land in the [dashboard](https://supabase.com/dashboard). The free tier is enough for local development.

## 2. Create a project

1. Open [New project](https://supabase.com/dashboard/new).
2. Pick your organization (a personal org is created automatically on first signup).
3. Set a **project name** (e.g. `Knowledge Base`).
4. Choose a **database password** — save it somewhere safe; you need it for direct DB access.
5. Pick a **region** close to you.
6. Click **Create new project** and wait until status is healthy (~1–2 minutes).

## 3. Collect credentials

| Value | Where to find it | Used by |
| ----- | ---------------- | ------- |
| **Direct database connection string** | Dashboard → **Project Settings** → **Database** → Connection string | Alembic migrations and backend DB access |
| **Database password** | What you set at project creation | Direct Postgres connection |

## 4. Qdrant (self-hosted vector DB)

We use Qdrant for vector storage instead of Supabase pgvector. Run it locally with Docker:

```bash
docker pull qdrant/qdrant
docker run -d --name qdrant \
  -p 6333:6333 -p 6334:6334 \
  -v qdrant_data:/qdrant/storage \
  qdrant/qdrant
```

Or add to `docker-compose.yml` alongside the backend:

```yaml
services:
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  qdrant_data:
```

Qdrant collections (embedding dimensions, distance metric, payload schema) are defined in `app/vector_db/setup.py` and initialized in a FastAPI startup hook. Do not create collections manually in the Qdrant dashboard.

## 5. Database schema management

This project uses Alembic from the Python backend to manage database schema. Do not create production tables manually in the Supabase dashboard.

Alembic migrations create and update:

- user and trial tables (users, trials, trial_members)
- document and document_chunk tables
- chat thread and message tables
- citation records
- evaluation run and result tables

Use the **direct/session** database connection string for Alembic. Do not use the transaction pooler connection string for migrations.

From `backend/`:

```bash
uv run alembic upgrade head
```

See [Backend setup](backend-setup.md) for the Alembic workflow.

## Next steps

- [Backend setup](backend-setup.md) — Python service + migrations
- [Frontend setup](frontend-setup.md) — React app
