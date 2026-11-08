from pocket.context import estimate_tokens, fit_context
from pocket.providers import Message


def m(role: str, chars: int) -> Message:
    return Message(role=role, content='x' * chars)


def test_a_short_conversation_is_kept_whole_after_the_system_prompt():
    history = [m('user', 30), m('assistant', 30), m('user', 30)]
    out = fit_context('be nice', history, context_tokens=4096, max_new_tokens=512)
    assert out[0].role == 'system'
    assert out[1:] == history


def test_the_oldest_turns_are_dropped_first():
    history = [
        m('user', 3000),
        m('assistant', 3000),
        m('user', 300),
        m('assistant', 300),
        m('user', 60),
    ]
    out = fit_context('sys', history, context_tokens=1200, max_new_tokens=512)
    assert out[-1] == history[-1]
    assert history[0] not in out
    budget = 1200 - 512
    assert sum(estimate_tokens(x) for x in out) <= budget + estimate_tokens(out[0])


def test_the_window_never_opens_with_an_assistant_turn():
    history = [m('user', 2400), m('assistant', 600), m('user', 30)]
    out = fit_context('sys', history, context_tokens=900, max_new_tokens=512)
    assert out[1].role == 'user'


def test_the_question_survives_even_when_nothing_else_fits():
    history = [m('user', 3000), m('assistant', 3000), m('user', 2000)]
    out = fit_context('sys', history, context_tokens=600, max_new_tokens=512)
    assert out == [out[0], history[-1]]
