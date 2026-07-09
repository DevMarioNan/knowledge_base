import tiktoken

_ENCODING = "cl100k_base"


def count_tokens(text: str) -> int:
    enc = tiktoken.get_encoding(_ENCODING)
    return len(enc.encode(text))


def count_message_tokens(messages: list[dict]) -> int:
    enc = tiktoken.get_encoding(_ENCODING)
    total = 0
    for msg in messages:
        total += 4
        total += len(enc.encode(msg.get("content", "")))
        total += len(enc.encode(msg.get("role", "")))
    total += 2
    return total


def truncate_to_token_limit(text: str, limit: int) -> str:
    enc = tiktoken.get_encoding(_ENCODING)
    tokens = enc.encode(text)
    if len(tokens) <= limit:
        return text
    return enc.decode(tokens[:limit])


def context_window_available(total_tokens: int, model_max: int = 128_000) -> int:
    return model_max - total_tokens
