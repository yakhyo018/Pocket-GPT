import json
import time
from collections.abc import AsyncIterator, Callable

from pocket.providers import ChatProvider, Message


def sse(event: str, data: dict) -> str:
    """One Server-Sent Event: `event:` names it, `data:` carries JSON, a blank line ends it."""
    return f'event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'


# no-transform / X-Accel-Buffering: proxies (nginx) must pass each event through at once.
SSE_HEADERS = {'Cache-Control': 'no-cache, no-transform', 'X-Accel-Buffering': 'no'}


async def stream_reply(
    provider: ChatProvider,
    messages: list[Message],
    max_new_tokens: int,
    temperature: float,
    on_finish: Callable[[str, bool], None] | None = None,
) -> AsyncIterator[str]:
    """
    `delta` events while the model writes, then `done` with timings (or one `error`).
    When the browser presses Stop it closes the connection and Starlette cancels this generator:
    generation stops, and `on_finish(text_so_far, stopped=True)` still saves what was written.
    """
    started = time.perf_counter()
    first: float | None = None
    parts: list[str] = []
    finished = False
    try:
        async for piece in provider.stream(messages, max_new_tokens, temperature):
            if first is None:
                first = time.perf_counter()
            parts.append(piece)
            yield sse('delta', {'text': piece})
        finished = True
    except Exception as err:  # the client gets one error event; details stay in the log
        yield sse('error', {'message': f'generation failed: {type(err).__name__}'})
        return
    finally:
        text = ''.join(parts)
        if on_finish and (finished or text):
            on_finish(text, not finished)
    ended = time.perf_counter()
    yield sse(
        'done',
        {
            'provider': provider.name,
            'pieces': len(parts),
            'first_token_ms': round(((first or ended) - started) * 1000),
            'total_ms': round((ended - started) * 1000),
        },
    )
