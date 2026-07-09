from collections.abc import AsyncIterator

import structlog
from openai import APIStatusError, AsyncOpenAI

from app.config import settings

logger = structlog.get_logger()

_client: AsyncOpenAI | None = None

_RETRYABLE_STATUSES = {429, 500, 502, 503}


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def generate(
    messages: list[dict],
    model: str | None = None,
    stream: bool = False,
    max_tokens: int = 2048,
    temperature: float = 0.0,
) -> str | AsyncIterator[str]:
    client = _get_client()
    resolved_model = model or settings.llm_model
    attempts = 0

    while attempts < 2:
        attempts += 1
        try:
            response = await client.chat.completions.create(
                model=resolved_model,
                messages=messages,
                stream=stream,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            if stream:
                return _stream_tokens(response)
            return response.choices[0].message.content or ""

        except APIStatusError as exc:
            if exc.status_code in _RETRYABLE_STATUSES and attempts < 2:
                logger.warning("llm_retry", status=exc.status_code, attempt=attempts)
                continue
            logger.error("llm_failed", status=exc.status_code, error=str(exc))
            raise


async def _stream_tokens(response) -> AsyncIterator[str]:
    async for chunk in response:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            yield delta.content
