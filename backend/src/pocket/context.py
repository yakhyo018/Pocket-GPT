"""
Fitting a conversation into the model's context window.

A model sees at most `context_tokens` tokens: the system prompt, the history and the reply it
writes. When a conversation grows past that, the oldest turns are dropped — the system prompt and
the newest user message always stay. Tokens are estimated, not counted: the backend does not
load the model's tokenizer, and the estimate errs on the safe side.
"""

from pocket.providers.base import Message

# Qwen's tokenizer averages ~4 characters per token in English and ~2.5–3 in Russian and Uzbek;
# 3 keeps a mixed conversation from overflowing. Each message also costs a few framing tokens.
CHARS_PER_TOKEN = 3
TOKENS_PER_MESSAGE = 6


def estimate_tokens(message: Message) -> int:
    return len(message.content) // CHARS_PER_TOKEN + TOKENS_PER_MESSAGE


def fit_context(
    system_prompt: str, history: list[Message], context_tokens: int, max_new_tokens: int
) -> list[Message]:
    """
    [system] + the newest messages that fit `context_tokens - max_new_tokens`, oldest dropped
    first, in their original order. The last message (the user's question) is always kept — if
    it alone is too long, the API's own limit (8,000 characters) has already rejected it.
    """
    system = Message(role='system', content=system_prompt)
    budget = context_tokens - max_new_tokens - estimate_tokens(system)
    kept: list[Message] = []
    for message in reversed(history):
        cost = estimate_tokens(message)
        if kept and cost > budget:
            break
        kept.append(message)
        budget -= cost
    # A reply must not open the window: drop a leading assistant turn left alone by the cut.
    while len(kept) > 1 and kept[-1].role == 'assistant':
        kept.pop()
    return [system, *reversed(kept)]
