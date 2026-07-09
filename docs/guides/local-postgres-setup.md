# Local PostgreSQL setup

We run PostgreSQL via Docker for local development. The `docker-compose.yml` at the project root includes both PostgreSQL and Qdrant services.

## 1. Docker Compose service

The PostgreSQL service is already defined in `docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: trialbase
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
```

## 2. Start the service

```bash
docker compose up -d
```

This starts both PostgreSQL and Qdrant. Data is persisted in named Docker volumes (`postgres_data`, `qdrant_storage`).

## 3. Connection details

| Variable | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| User | `postgres` |
| Password | `postgres` |
| Database | `trialbase` |
| Connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/trialbase` |

## 4. Run migrations

Alembic manages the database schema. From `backend/`:

```bash
cd backend
uv run alembic upgrade head
```

This creates all tables defined in the SQLAlchemy models.

## 5. Seed data (optional)

If seed scripts exist under `backend/scripts/`, run them after migrations:

```bash
cd backend
uv run python scripts/seed.py
```

## 6. Inspect the database

Connect with any PostgreSQL client:

```bash
psql postgresql://postgres:postgres@localhost:5432/trialbase
```

## Next steps

- [Backend setup](backend-setup.md) — Python service + migrations
- [Frontend setup](frontend-setup.md) — React app
