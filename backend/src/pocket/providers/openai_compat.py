import json
from collections.abc import AsyncIterator

import httpx

from pocket.providers.base import Message


class OpenAICompatProvider:
    """
    One client for every server that speaks OpenAI's `POST /v1/chat/completions` with
    `stream: true`: llama.cpp's `llama-server` (the local GGUF model) and OpenRouter (hosted
    models). The stream is Server-Sent Events: `data: {...choices[0].delta.content...}` lines,
    then `data: [DONE]`.
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        model: str = '',
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.name = name
        self._url = base_url.rstrip('/') + '/v1/chat/completions'
        self._model = model
        self._headers = {'Content-Type': 'application/json'}
        if api_key:
            self._headers['Authorization'] = f'Bearer {api_key}'
        # connect fails fast (server not running); read waits for slow first tokens on a CPU.
        self._timeout = httpx.Timeout(timeout, connect=5.0)

    async def stream(
        self, messages: list[Message], max_new_tokens: int, temperature: float
    ) -> AsyncIterator[str]:
        body = {
            'messages': [m.model_dump() for m in messages],
            'max_tokens': max_new_tokens,
            'temperature': temperature,
            'stream': True,
        }
        if self._model:
            body['model'] = self._model
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream('POST', self._url, headers=self._headers, json=body) as resp:
                if resp.status_code != 200:
                    await resp.aread()
                    raise RuntimeError(f'{self.name} answered {resp.status_code}')
                async for line in resp.aiter_lines():
                    piece = parse_sse_line(line)
                    if piece is None:
                        continue
                    if piece == '[DONE]':
                        return
                    yield piece


def parse_sse_line(line: str) -> str | None:
    """`data: {...}` → the text delta; `data: [DONE]` → '[DONE]'; anything else → None."""
    if not line.startswith('data:'):
        return None
    payload = line[5:].strip()
    if payload == '[DONE]':
        return '[DONE]'
    try:
        chunk = json.loads(payload)
    except json.JSONDecodeError:
        return None
    choices = chunk.get('choices') or []
    if not choices:
        return None
    text = (choices[0].get('delta') or {}).get('content')
    return text or None
