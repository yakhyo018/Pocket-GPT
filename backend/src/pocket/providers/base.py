from collections.abc import AsyncIterator
from typing import Literal, Protocol

from pydantic import BaseModel, Field

Role = Literal['system', 'user', 'assistant']


class Message(BaseModel):
    role: Role
    content: str = Field(min_length=1, max_length=8000)


class ChatProvider(Protocol):
    """
    Every model PocketGPT can talk to: the fake one, the local llama.cpp server, OpenRouter.
    The API depends on this shape only, so switching models is a setting, not a code change.
    """

    name: str

    def stream(
        self, messages: list[Message], max_new_tokens: int, temperature: float
    ) -> AsyncIterator[str]:
        """Yields the reply piece by piece (a token or a few characters at a time)."""
        ...
