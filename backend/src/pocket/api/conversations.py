from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from pocket.api.streaming import SSE_HEADERS, stream_reply
from pocket.context import fit_context
from pocket.providers import Message
from pocket.store import Store

router = APIRouter(prefix='/v1/conversations', tags=['conversations'])


class NewMessage(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


def _store(request: Request) -> Store:
    return request.app.state.store


def _existing(request: Request, conversation_id: str):
    conversation = _store(request).get(conversation_id)
    if not conversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'conversation not found')
    return conversation


@router.get('')
def list_conversations(request: Request) -> list[dict]:
    return [asdict(c) for c in _store(request).recent()]


@router.post('', status_code=status.HTTP_201_CREATED)
def create_conversation(request: Request) -> dict:
    return asdict(_store(request).create())


@router.get('/{conversation_id}')
def get_conversation(conversation_id: str, request: Request) -> dict:
    conversation = _existing(request, conversation_id)
    messages = [asdict(m) for m in _store(request).messages(conversation_id)]
    return {**asdict(conversation), 'messages': messages}


@router.delete('/{conversation_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: str, request: Request) -> Response:
    if not _store(request).delete(conversation_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'conversation not found')
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post('/{conversation_id}/messages')
async def send_message(conversation_id: str, payload: NewMessage, request: Request):
    """
    The user's message is saved first, then the reply streams; the reply is saved when it ends —
    or, after Stop, with what was written so far and `stopped = true`.
    """
    _existing(request, conversation_id)
    store = _store(request)
    s = request.app.state.settings
    store.add(conversation_id, 'user', payload.content)
    history = [Message(role=m.role, content=m.content) for m in store.messages(conversation_id)]
    messages = fit_context(s.system_prompt, history, s.context_tokens, s.max_new_tokens)

    def save(text: str, stopped: bool) -> None:
        if text:
            store.add(conversation_id, 'assistant', text, stopped=stopped)

    events = stream_reply(
        request.app.state.provider, messages, s.max_new_tokens, s.temperature, on_finish=save
    )
    return StreamingResponse(events, media_type='text/event-stream', headers=SSE_HEADERS)
