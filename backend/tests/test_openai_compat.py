from pocket.providers.openai_compat import parse_sse_line


def test_reads_a_delta_and_the_end():
    line = 'data: {"choices":[{"delta":{"content":"Sal"}}]}'
    assert parse_sse_line(line) == 'Sal'
    assert parse_sse_line('data: [DONE]') == '[DONE]'


def test_ignores_what_is_not_text():
    assert parse_sse_line('') is None
    assert parse_sse_line(': keep-alive') is None
    assert parse_sse_line('data: {"choices":[{"delta":{"role":"assistant"}}]}') is None
    assert parse_sse_line('data: {"choices":[]}') is None
    assert parse_sse_line('data: not json') is None
