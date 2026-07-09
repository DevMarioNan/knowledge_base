from dataclasses import dataclass


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    content: str
    score: float
    source_filename: str
    page_number: int | None = None
    section_title: str | None = None
    section_number: str | None = None
    chunk_index: int = 0
    rerank_score: float | None = None
