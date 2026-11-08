from pocket.store import make_title
from tests.test_chat import parse


def test_a_conversation_keeps_both_sides_and_names_itself(client):
    conv = client.post('/v1/conversations').json()
    assert conv['title'] == ''
    reply = client.post(f'/v1/conversations/{conv["id"]}/messages', json={'content': 'Hello there'})
    assert parse(reply.text)[-1][0] == 'done'
    stored = client.get(f'/v1/conversations/{conv["id"]}').json()
    assert stored['title'] == 'Hello there'
    assert [x['role'] for x in stored['messages']] == ['user', 'assistant']
    assert stored['messages'][1]['content'].startswith('Hi!')
    assert stored['messages'][1]['stopped'] is False


def test_the_list_shows_the_newest_first_and_delete_removes(client):
    first = client.post('/v1/conversations').json()['id']
    second = client.post('/v1/conversations').json()['id']
    client.post(f'/v1/conversations/{first}/messages', json={'content': 'later'})
    ids = [c['id'] for c in client.get('/v1/conversations').json()]
    assert ids[0] == first and second in ids
    assert client.delete(f'/v1/conversations/{first}').status_code == 204
    assert client.get(f'/v1/conversations/{first}').status_code == 404
    assert client.delete(f'/v1/conversations/{first}').status_code == 404


def test_an_unknown_conversation_is_404(client):
    reply = client.post('/v1/conversations/nope/messages', json={'content': 'hi'})
    assert reply.status_code == 404


def test_a_long_first_message_is_cut_at_a_word():
    title = make_title('word ' * 40)
    assert len(title) <= 61 and title.endswith('…') and not title.endswith(' …')
