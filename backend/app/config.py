import sys

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "knowledge-base"
    debug: bool = False

    database_url: str
    openai_api_key: str
    cohere_api_key: str
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    allowed_domains: str = ""

    @property
    def allowed_domains_list(self) -> list[str]:
        if not self.allowed_domains.strip():
            return []
        return [d.strip() for d in self.allowed_domains.split(",") if d.strip()]

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    llm_model: str = "gpt-4o-mini"
    cohere_rerank_model: str = "rerank-v3.5"

    vector_collection_name: str = "documents"

    max_upload_size_mb: int = 50
    storage_path: str = "storage"
    chunk_size: int = 1000
    chunk_overlap: int = 200

    log_level: str = "INFO"
    log_json: bool = True


try:
    settings = Settings()
except ValidationError as e:
    missing = [err["loc"][0] for err in e.errors() if err["type"] == "missing"]
    print("FATAL: Required environment variables are missing:", file=sys.stderr)
    for var in missing:
        print(f"  - {var}", file=sys.stderr)
    print(
        "Check your .env file or set these environment variables before starting the server.",
        file=sys.stderr,
    )
    sys.exit(1)
