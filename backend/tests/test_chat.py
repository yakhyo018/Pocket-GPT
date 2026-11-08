import json

import pytest

from pocket.core.config import Settings
from pocket.providers import create_provider


def parse(body: str) -> list[tuple[str, dict]]:
    """Server-Sent Events → [(event, data)]."""
    events = []
    for block in body.strip().split('\n\n'):
        lines = dict(line.split(': ', 1) for line in block.split('\n'))
        events.append((lines['event'], json.loads(lines['data'])))
    return events


def test_health_names_the_provider(client):
    body = client.get('/health').json()
    assert body['status'] == 'ok'
    assert body['provider'] == 'fake'


@pytest.mark.parametrize(
    ('question', 'expected'),
    [('Hello there', 'Hi!'), ('Привет, как дела?', 'Привет!'), ('Salom, qandaysan?', 'Salom!')],
)
def test_chat_streams_in_the_question_language(client, question, expected):
    response = client.post('/v1/chat', json={'messages': [{'role': 'user', 'content': question}]})
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/event-stream')
    events = parse(response.text)
    deltas = [data['text'] for name, data in events if name == 'delta']
    assert len(deltas) > 3, 'the reply must arrive in pieces, not at once'
    assert ''.join(deltas).startswith(expected)
    assert events[-1][0] == 'done'
    assert events[-1][1]['pieces'] == len(deltas)


def test_the_last_message_must_be_the_users(client):
    messages = [
        {'role': 'user', 'content': 'hi'},
        {'role': 'assistant', 'content': 'hello'},
    ]
    assert client.post('/v1/chat', json={'messages': messages}).status_code == 422


@pytest.mark.parametrize(
    'payload',
    [
        {'messages': []},
        {'messages': [{'role': 'robot', 'content': 'hi'}]},
        {'messages': [{'role': 'user', 'content': ''}]},
        {'messages': [{'role': 'user', 'content': 'x' * 8001}]},
    ],
)
def test_bad_input_is_422(client, payload):
    assert client.post('/v1/chat', json=payload).status_code == 422


def test_cors_allows_only_the_web_origin(client, settings):
    ok = client.options(
        '/v1/chat',
        headers={'Origin': settings.web_origin, 'Access-Control-Request-Method': 'POST'},
    )
    assert ok.headers.get('access-control-allow-origin') == settings.web_origin
    bad = client.options(
        '/v1/chat',
        headers={'Origin': 'https://evil.example', 'Access-Control-Request-Method': 'POST'},
    )
    assert 'access-control-allow-origin' not in bad.headers


def test_openrouter_without_a_key_stops_the_boot():
    with pytest.raises(RuntimeError, match='POCKET_OPENROUTER_API_KEY'):
        create_provider(Settings(_env_file=None, provider='openrouter'))
