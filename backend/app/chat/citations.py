import re

from app.retrieval.types import RetrievedChunk  # noqa: F401

_CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def parse_citations(text: str, chunks: list[RetrievedChunk]) -> list[dict]:
    seen: set[int] = set()
    citations: list[dict] = []

    for match in _CITATION_PATTERN.finditer(text):
        idx = int(match.group(1))
        if idx in seen:
            continue
        seen.add(idx)

        if 1 <= idx <= len(chunks):
            chunk = chunks[idx - 1]
            citations.append({
                "citation_index": idx,
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "content_excerpt": chunk.content[:300],
                "page_number": chunk.page_number,
                "relevance_score": chunk.rerank_score or chunk.score,
            })

    return citations


def validate_grounding(text: str, chunks: list[RetrievedChunk]) -> bool:
    if not chunks:
        return False

    matches = _CITATION_PATTERN.findall(text)
    if not matches:
        lowered = text.lower()
        if "i don't know" in lowered or "don't know based" in lowered:
            return True
        return False

    for m in matches:
        idx = int(m)
        if 1 <= idx <= len(chunks):
            return True

    return False
