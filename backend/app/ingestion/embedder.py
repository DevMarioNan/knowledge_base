import tiktoken
from openai import AsyncOpenAI

from app.config import settings

_client: AsyncOpenAI | None = None

_EMBEDDING_MODEL_MAX_TOKENS: dict[str, int] = {
    "text-embedding-3-small": 8192,
    "text-embedding-3-large": 8192,
    "text-embedding-ada-002": 8192,
}
_TRUNCATE_SAFETY_MARGIN = 100


def _truncate_text(text: str, max_tokens: int, enc: tiktoken.Encoding) -> str:
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return enc.decode(tokens[:max_tokens])


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def embed_texts(texts: list[str]) -> list[list[float]]:
    client = _get_client()
    model_max_tokens = _EMBEDDING_MODEL_MAX_TOKENS.get(
        settings.embedding_model, 8192
    )
    safe_limit = model_max_tokens - _TRUNCATE_SAFETY_MARGIN
    enc = tiktoken.get_encoding("cl100k_base")

    truncated = [_truncate_text(t, safe_limit, enc) for t in texts]

    response = await client.embeddings.create(
        input=truncated,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
    return [item.embedding for item in response.data]
