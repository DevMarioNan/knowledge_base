from dataclasses import dataclass, field
from pathlib import Path

import structlog

logger = structlog.get_logger()


@dataclass
class ParsedPage:
    page_number: int
    text: str
    sections: list[dict] = field(default_factory=list)


@dataclass
class ParseResult:
    pages: list[ParsedPage]
    metadata: dict | None = None


async def parse_pdf(file_path: Path) -> ParseResult:
    try:
        return _parse_with_pymupdf(file_path)
    except Exception as exc:
        logger.warning("pymupdf_failed_falling_back", error=str(exc))
        return _parse_with_pdfminer(file_path)


def _parse_with_pymupdf(file_path: Path) -> ParseResult:
    import fitz

    doc = fitz.open(file_path)
    pages: list[ParsedPage] = []
    toc = doc.get_toc()

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if not text.strip():
            continue

        parsed = ParsedPage(page_number=page_num + 1, text=text.strip())

        if toc:
            for item in toc:
                level, title, target_page = item
                if target_page == page_num + 1:
                    parsed.sections.append({"level": level, "title": title})

        pages.append(parsed)

    doc.close()

    return ParseResult(
        pages=pages,
        metadata={"page_count": len(pages), "parser": "pymupdf"},
    )


def _parse_with_pdfminer(file_path: Path) -> ParseResult:
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTTextBox, LTTextLine

    pages: list[ParsedPage] = []
    for i, page_layout in enumerate(extract_pages(file_path)):
        text_parts: list[str] = []
        for element in page_layout:
            if isinstance(element, (LTTextBox, LTTextLine)):
                text_parts.append(element.get_text())
        text = "".join(text_parts).strip()
        if text:
            pages.append(ParsedPage(page_number=i + 1, text=text))

    return ParseResult(
        pages=pages,
        metadata={"page_count": len(pages), "parser": "pdfminer"},
    )
