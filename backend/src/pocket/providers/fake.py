import asyncio
from collections.abc import AsyncIterator

from pocket.providers.base import Message

# One canned reply per script: the fake answers in the language of the question, like the real
# model must — the UI and the tests see the same behaviour without a GPU.
_REPLIES = {
    'cyrillic': 'Привет! Я PocketGPT в тестовом режиме. Настоящая модель подключится позже.',
    'uz': 'Salom! Men PocketGPT, hozir test rejimidaman. Haqiqiy model keyinroq ulanadi.',
    'en': 'Hi! I am PocketGPT in test mode. The real model is connected in a later step.',
}
_UZ_HINTS = ("o'", "g'", 'salom', 'qanday', 'nima', 'rahmat')


def _language(text: str) -> str:
    if any(0x0400 <= ord(ch) <= 0x04FF for ch in text):  # the Cyrillic block
        return 'cyrillic'
    lowered = text.lower()
    return 'uz' if any(hint in lowered for hint in _UZ_HINTS) else 'en'


class FakeProvider:
    """Streams a fixed reply word by word with a small delay — enough to build streaming on."""

    name = 'fake'

    def __init__(self, delay: float = 0.04) -> None:
        self._delay = delay

    async def stream(
        self, messages: list[Message], max_new_tokens: int, temperature: float
    ) -> AsyncIterator[str]:
        last_user = next((m.content for m in reversed(messages) if m.role == 'user'), '')
        words = _REPLIES[_language(last_user)].split(' ')
        for index, word in enumerate(words[:max_new_tokens]):
            await asyncio.sleep(self._delay)
            yield word if index == 0 else f' {word}'
