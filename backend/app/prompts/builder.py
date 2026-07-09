from app.llm.tokens import count_tokens, truncate_to_token_limit
from app.prompts.system import SYSTEM_PROMPT
from app.retrieval.types import RetrievedChunk

_CONTEXT_WINDOW_SAFETY_MARGIN = 4096


def build_context(chunks: list[RetrievedChunk]) -> str:
    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        meta_parts: list[str] = []
        if chunk.section_title:
            meta_parts.append(f'section "{chunk.section_title}"')
        if chunk.page_number is not None:
            meta_parts.append(f"page {chunk.page_number}")
        if chunk.source_filename:
            meta_parts.append(chunk.source_filename)

        meta = f" ({'; '.join(meta_parts)})" if meta_parts else ""
        parts.append(f"[{i}]{meta}\n{chunk.content}")
    return "\n\n".join(parts)


def build_history(messages: list[dict]) -> str:
    if not messages:
        return "(no prior conversation)"
    lines: list[str] = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        lines.append(f"{role.capitalize()}: {content}")
    return "\n".join(lines)


def build_messages(
    query: str,
    chunks: list[RetrievedChunk],
    history: list[dict] | None = None,
    model_max_tokens: int = 128_000,
) -> list[dict]:
    history = history or []
    history_str = build_history(history)
    max_context_tokens = model_max_tokens - _CONTEXT_WINDOW_SAFETY_MARGIN

    context = build_context(chunks)
    for attempt in range(len(chunks)):
        prompt = SYSTEM_PROMPT.format(context=context, history=history_str, query=query)
        total = count_tokens(prompt)
        if total <= max_context_tokens:
            return [{"role": "system", "content": prompt}]
        if not chunks:
            break
        chunks = chunks[:-1]
        context = build_context(chunks)

    return [{"role": "system", "content": prompt}]
