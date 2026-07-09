import math
from collections import Counter

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

logger = structlog.get_logger()

_RRF_K = 60


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def _bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    avg_doc_len: float,
    num_docs: int,
    doc_freqs: dict[str, int],
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    doc_len = len(doc_tokens)
    doc_counter = Counter(doc_tokens)
    score = 0.0
    for token in set(query_tokens):
        tf = doc_counter.get(token, 0)
        if tf == 0:
            continue
        df = doc_freqs.get(token, 1)
        idf = math.log((num_docs - df + 0.5) / (df + 0.5) + 1.0)
        tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_doc_len))
        score += idf * tf_norm
    return score


def _compute_bm25_scores(
    query: str,
    chunks: list[dict],
    all_texts: list[str],
) -> dict[str, float]:
    query_tokens = _tokenize(query)
    num_docs = len(all_texts)
    if num_docs == 0:
        return {}

    tokenized_docs = [_tokenize(t) for t in all_texts]
    avg_doc_len = sum(len(t) for t in tokenized_docs) / max(num_docs, 1)

    doc_freqs: dict[str, int] = {}
    for tokens in tokenized_docs:
        for token in set(tokens):
            doc_freqs[token] = doc_freqs.get(token, 0) + 1

    id_to_score: dict[str, float] = {}
    for chunk, tokens in zip(chunks, tokenized_docs):
        chunk_id = chunk.get("chunk_id", "")
        id_to_score[chunk_id] = _bm25_score(query_tokens, tokens, avg_doc_len, num_docs, doc_freqs)

    return id_to_score


def _chunk_from_point(point) -> dict | None:
    payload = point.payload or {}
    if not payload.get("content"):
        return None
    return {
        "chunk_id": payload.get("chunk_id", ""),
        "document_id": payload.get("document_id", ""),
        "content": payload.get("content", ""),
        "score": point.score,
        "source_filename": payload.get("source_filename", ""),
        "page_number": payload.get("page_number"),
        "section_title": payload.get("section_title"),
        "section_number": payload.get("section_number"),
        "chunk_index": payload.get("chunk_index", 0),
    }


async def dense_search(
    qdrant: AsyncQdrantClient,
    collection: str,
    trial_id: str,
    query_vector: list[float],
    top_k: int,
) -> list[dict]:
    response = await qdrant.query_points(
        collection_name=collection,
        query=query_vector,
        query_filter=qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="trial_id",
                    match=qmodels.MatchValue(value=trial_id),
                ),
            ],
        ),
        limit=top_k,
    )
    chunks: list[dict] = []
    for point in response.points:
        chunk = _chunk_from_point(point)
        if chunk:
            chunks.append(chunk)
    return chunks


async def bm25_search(
    qdrant: AsyncQdrantClient,
    collection: str,
    trial_id: str,
    query_text: str,
    top_k: int,
) -> list[dict]:
    scroll_limit = max(top_k * 10, 200)
    all_points: list = []
    next_offset: str | None = None

    while len(all_points) < scroll_limit:
        result = await qdrant.scroll(
            collection_name=collection,
            limit=scroll_limit,
            offset=next_offset,
            scroll_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="trial_id",
                        match=qmodels.MatchValue(value=trial_id),
                    ),
                ],
            ),
            with_payload=True,
            with_vectors=False,
        )
        points, next_offset = result
        all_points.extend(points)
        if not next_offset:
            break

    if not all_points:
        return []

    chunks: list[dict] = []
    all_texts: list[str] = []
    for point in all_points:
        payload = point.payload or {}
        content = payload.get("content", "")
        if not content:
            continue
        chunks.append({
            "chunk_id": payload.get("chunk_id", ""),
            "document_id": payload.get("document_id", ""),
            "content": content,
            "score": 0.0,
            "source_filename": payload.get("source_filename", ""),
            "page_number": payload.get("page_number"),
            "section_title": payload.get("section_title"),
            "section_number": payload.get("section_number"),
            "chunk_index": payload.get("chunk_index", 0),
        })
        all_texts.append(content)

    bm25_scores = _compute_bm25_scores(query_text, chunks, all_texts)
    for chunk in chunks:
        chunk["score"] = bm25_scores.get(chunk["chunk_id"], 0.0)

    chunks.sort(key=lambda c: c["score"], reverse=True)
    return chunks[:top_k]


def rrf_fusion(dense: list[dict], sparse: list[dict], k: int = _RRF_K) -> list[dict]:
    seen: dict[str, dict] = {}

    for rank, item in enumerate(dense):
        cid = item["chunk_id"]
        item["rrf_score"] = 1.0 / (k + rank + 1)
        seen[cid] = item

    for rank, item in enumerate(sparse):
        cid = item["chunk_id"]
        rrf = 1.0 / (k + rank + 1)
        if cid in seen:
            seen[cid]["rrf_score"] = seen[cid].get("rrf_score", 0.0) + rrf
        else:
            item["rrf_score"] = rrf
            seen[cid] = item

    fused = sorted(seen.values(), key=lambda x: x["rrf_score"], reverse=True)
    return fused


async def hybrid_search(
    qdrant: AsyncQdrantClient,
    collection: str,
    trial_id: str,
    query_text: str,
    query_vector: list[float],
    top_k: int,
) -> list[dict]:
    dense_results = await dense_search(qdrant, collection, trial_id, query_vector, top_k)
    sparse_results = await bm25_search(qdrant, collection, trial_id, query_text, top_k)

    if not sparse_results:
        logger.info("bm25_no_results", trial_id=trial_id)
        return dense_results

    fused = rrf_fusion(dense_results, sparse_results)
    return fused[:top_k]
