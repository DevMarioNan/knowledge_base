import cohere
import structlog

from app.config import settings
from app.retrieval.types import RetrievedChunk

logger = structlog.get_logger()

_client: cohere.AsyncClient | None = None


def _get_client() -> cohere.AsyncClient:
    global _client
    if _client is None:
        _client = cohere.AsyncClient(api_key=settings.cohere_api_key)
    return _client


async def rerank(
    query: str,
    chunks: list[RetrievedChunk],
    model: str | None = None,
    top_n: int = 5,
) -> list[RetrievedChunk]:
    if not chunks:
        return []

    client = _get_client()
    resolved_model = model or settings.cohere_rerank_model

    try:
        response = await client.rerank(
            model=resolved_model,
            query=query,
            documents=[c.content for c in chunks],
            top_n=min(top_n, len(chunks)),
        )
    except Exception as exc:
        logger.error("rerank_failed", error=str(exc))
        return chunks[:top_n]

    reranked: list[RetrievedChunk] = []
    for result in response.results:
        idx = result.index
        if idx < len(chunks):
            chunk = chunks[idx]
            chunk.rerank_score = result.relevance_score
            chunk.score = result.relevance_score
            reranked.append(chunk)

    return reranked
