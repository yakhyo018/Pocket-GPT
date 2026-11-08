from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from pocket.api.streaming import SSE_HEADERS, stream_reply
from pocket.context import fit_context
from pocket.providers import Message

router = APIRouter(prefix='/v1', tags=['chat'])

# One request's cap; the conversation is then trimmed to the model's context window.
MAX_TOTAL_CHARS = 32_000


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=50)

    @field_validator('messages')
    @classmethod
    def ends_with_user(cls, messages: list[Message]) -> list[Message]:
        if messages[-1].role != 'user':
            raise ValueError('the last message must come from the user')
        if sum(len(m.content) for m in messages) > MAX_TOTAL_CHARS:
            raise ValueError(f'the conversation is longer than {MAX_TOTAL_CHARS} characters')
        return messages


@router.post('/chat')
async def chat(payload: ChatRequest, request: Request) -> StreamingResponse:
    """Stateless: the client sends the whole history (the evaluation script uses this)."""
    s = request.app.state.settings
    history = [m for m in payload.messages if m.role != 'system']
    messages = fit_context(s.system_prompt, history, s.context_tokens, s.max_new_tokens)
    events = stream_reply(request.app.state.provider, messages, s.max_new_tokens, s.temperature)
    return StreamingResponse(events, media_type='text/event-stream', headers=SSE_HEADERS)
