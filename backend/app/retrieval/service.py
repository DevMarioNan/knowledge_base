from qdrant_client import AsyncQdrantClient

from app.config import settings
from app.ingestion.embedder import embed_texts
from app.retrieval.hybrid import hybrid_search
from app.retrieval.reranker import rerank
from app.retrieval.types import RetrievedChunk


def _to_retrieved_chunks(chunks: list[dict]) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk_id=c["chunk_id"],
            document_id=c["document_id"],
            content=c["content"],
            score=c.get("rrf_score", c.get("score", 0.0)),
            source_filename=c.get("source_filename", ""),
            page_number=c.get("page_number"),
            section_title=c.get("section_title"),
            section_number=c.get("section_number"),
            chunk_index=c.get("chunk_index", 0),
        )
        for c in chunks
    ]


async def retrieve(
    qdrant: AsyncQdrantClient,
    trial_id: str,
    query: str,
    top_k: int = 10,
    top_n: int = 5,
    rerank_model: str | None = None,
) -> list[RetrievedChunk]:
    vectors = await embed_texts([query])
    query_vector = vectors[0]

    raw_chunks = await hybrid_search(
        qdrant=qdrant,
        collection=settings.vector_collection_name,
        trial_id=trial_id,
        query_text=query,
        query_vector=query_vector,
        top_k=top_k,
    )

    retrieved = _to_retrieved_chunks(raw_chunks)

    reranked = await rerank(
        query=query,
        chunks=retrieved,
        model=rerank_model,
        top_n=top_n,
    )

    return reranked
