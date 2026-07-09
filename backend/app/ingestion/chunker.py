from dataclasses import dataclass

from app.config import settings
from app.ingestion.parser import ParsedPage, ParseResult


@dataclass
class Chunk:
    content: str
    chunk_index: int
    page_number: int | None = None
    section_title: str | None = None
    section_number: str | None = None
    token_count: int | None = None


def chunk_document(parse_result: ParseResult) -> list[Chunk]:
    full_text = "\n\n".join(p.text for p in parse_result.pages)

    section_chunks = _try_section_split(full_text, parse_result.pages)
    if section_chunks:
        return section_chunks

    return _recursive_character_split(full_text, len(section_chunks) if section_chunks else 0)


def _try_section_split(full_text: str, pages: list[ParsedPage]) -> list[Chunk]:
    import re

    heading_pattern = re.compile(r"^(#{1,3}\s+|(?:\d+\.)+\s+|[A-Z][A-Z\s]{2,})$", re.MULTILINE)
    splits = list(heading_pattern.finditer(full_text))
    if not splits:
        return []

    chunks: list[Chunk] = []
    prev_end = 0
    for idx, match in enumerate(splits):
        start = match.start()
        if start > prev_end:
            text = full_text[prev_end:start].strip()
            if text:
                section_title = match.group(0).strip().rstrip("#").strip()
                page = _find_page_for_offset(start, pages)
                chunks.append(
                    Chunk(
                        content=text,
                        chunk_index=len(chunks),
                        page_number=page.page_number if page else None,
                        section_title=section_title,
                        token_count=_count_tokens(text),
                    )
                )
        prev_end = start

    tail = full_text[prev_end:].strip()
    if tail:
        chunks.append(
            Chunk(
                content=tail,
                chunk_index=len(chunks),
                token_count=_count_tokens(tail),
            )
        )

    return chunks


def _recursive_character_split(full_text: str, start_index: int) -> list[Chunk]:
    separators = ["\n\n", "\n", ". ", " ", ""]
    chunks: list[Chunk] = []

    def _split(text: str, seps: list[str], target_size: int, overlap: int) -> list[str]:
        if not seps:
            return [text]

        sep = seps[0]
        parts: list[str] = []
        current = text

        while len(current) > target_size:
            split_at = current.rfind(sep, 0, target_size)
            if split_at == -1 or len(seps) > 1 and split_at < target_size // 2:
                return _split(text, seps[1:], target_size, overlap)

            parts.append(current[:split_at].strip())
            current = current[max(0, split_at - overlap):].strip()

        parts.append(current.strip())
        return [p for p in parts if p]

    raw_chunks = _split(full_text, list(separators), settings.chunk_size, settings.chunk_overlap)

    for i, text in enumerate(raw_chunks):
        chunks.append(
            Chunk(
                content=text,
                chunk_index=start_index + i,
                token_count=_count_tokens(text),
            )
        )

    return chunks


def _find_page_for_offset(offset: int, pages: list[ParsedPage]) -> ParsedPage | None:
    char_count = 0
    for page in pages:
        char_count += len(page.text) + 2
        if offset < char_count:
            return page
    return pages[-1] if pages else None


def _count_tokens(text: str) -> int:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        return len(text) // 4
