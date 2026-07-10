FROM python:3.12-slim AS builder

WORKDIR /app

COPY pyproject.toml .

RUN pip install --no-cache-dir --user .

FROM python:3.12-slim AS production

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local

COPY alembic.ini .
COPY alembic/ ./alembic/
COPY app/ ./app/

RUN mkdir -p /app/storage

ENV PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -sf http://localhost:8000/docs || exit 1

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
