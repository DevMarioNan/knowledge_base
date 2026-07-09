import json


def sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


async def token_event(content: str) -> str:
    return sse_event({"type": "token", "content": content})


async def citations_event(citations: list[dict]) -> str:
    return sse_event({"type": "citations", "citations": citations})


async def done_event(message_id: str) -> str:
    return sse_event({"type": "done", "message_id": message_id})


async def grounding_failure_event(message: str = "") -> str:
    return sse_event({
        "type": "grounding_failure",
        "message": message or "I don't know based on the provided documents",
    })


async def error_event(message: str) -> str:
    return sse_event({"type": "error", "message": message})


async def thread_event(thread_id: str, title: str) -> str:
    return sse_event({"type": "thread", "thread_id": thread_id, "title": title})
