"""
C2 — the PocketGPT chat dataset: English, Russian and Uzbek, balanced, with a frozen test set.

Sources (all Apache-2.0, see data/README.md):
- CohereLabs/aya_dataset — questions and answers written by people, per language (eng, rus);
- OpenAssistant/oasst2 — conversation trees written by volunteers: Russian first turns with
  their best-ranked reply (Aya alone has ~340 usable Russian rows);
- UAzimov/uzbek-instruct-llm — Uzbek instruction chats (`messages`), largely translated.

Every example is rewritten into the same shape the app serves: PocketGPT's system prompt, then
the user turn, then the assistant turn. Train like you serve: the model learns the exact frame it
will see. The test split is drawn first, from a fixed seed, and never changes after.

    python training/build_dataset.py            # → data/pocket_chat/{train,val,test}.jsonl
"""

import hashlib
import json
import random
from pathlib import Path

from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'pocket_chat'

# Must equal POCKET_SYSTEM_PROMPT's default in backend/src/pocket/core/config.py.
SYSTEM_PROMPT = (
    "You are PocketGPT, a helpful assistant running on the user's own computer. "
    "Always answer in the language of the user's last message (English, Russian or Uzbek). "
    'Be concise. If you do not know, say so.'
)
# 1,200 a language: Russian has ~1,480 usable rows after dedupe (Aya + OASST2), and the
# languages stay equal so none dominates the loss.
PER_LANGUAGE = {'train': 1200, 'val': 50, 'test': 100}
MIN_CHARS, MAX_USER_CHARS, MAX_ANSWER_CHARS = 8, 2000, 3000
SEED = 2026


def clean(text: str) -> str:
    return '\n'.join(line.rstrip() for line in str(text).strip().splitlines()).strip()


def usable(user: str, answer: str) -> bool:
    return (
        MIN_CHARS <= len(user) <= MAX_USER_CHARS
        and MIN_CHARS <= len(answer) <= MAX_ANSWER_CHARS
        and user != answer
    )


def example(user: str, answer: str, lang: str, source: str) -> dict:
    return {
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': user},
            {'role': 'assistant', 'content': answer},
        ],
        'lang': lang,
        'source': source,
    }


def aya(lang_code: str, lang: str) -> list[dict]:
    rows = load_dataset('CohereLabs/aya_dataset', split='train')
    rows = rows.filter(lambda r: r['language_code'] == lang_code)
    out = []
    for r in rows:
        user, answer = clean(r['inputs']), clean(r['targets'])
        if usable(user, answer):
            out.append(example(user, answer, lang, 'aya_dataset'))
    return out


def oasst(lang_code: str, lang: str) -> list[dict]:
    """First turns only: a root prompt (no parent) and its assistant reply ranked best (rank 0)."""
    rows = load_dataset('OpenAssistant/oasst2', split='train')
    rows = rows.filter(lambda r: r['lang'] == lang_code and not r['deleted'])
    roots = {r['message_id']: r['text'] for r in rows if r['parent_id'] is None}
    out = []
    for r in rows:
        if r['role'] == 'assistant' and r['rank'] == 0 and r['parent_id'] in roots:
            user, answer = clean(roots[r['parent_id']]), clean(r['text'])
            if usable(user, answer):
                out.append(example(user, answer, lang, 'oasst2'))
    return out


def uzbek() -> list[dict]:
    out = []
    for r in load_dataset('UAzimov/uzbek-instruct-llm', split='train'):
        msgs = r['messages']
        system = clean(next((m['content'] for m in msgs if m['role'] == 'system'), ''))
        user = clean(next((m['content'] for m in msgs if m['role'] == 'user'), ''))
        answer = clean(next((m['content'] for m in msgs if m['role'] == 'assistant'), ''))
        # The source keeps reading passages in its system turn; ours is fixed, so the passage
        # moves into the question, where the model needs it.
        if system:
            user = f'{system}\n\n{user}'
        if usable(user, answer):
            out.append(example(user, answer, 'UZ', 'uzbek-instruct-llm'))
    return out


def dedupe(rows: list[dict]) -> list[dict]:
    seen, out = set(), []
    for r in rows:
        key = hashlib.sha256(r['messages'][1]['content'].lower().encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def main() -> None:
    pools = {'EN': aya('eng', 'EN'), 'RU': aya('rus', 'RU') + oasst('ru', 'RU'), 'UZ': uzbek()}
    splits: dict[str, list[dict]] = {'train': [], 'val': [], 'test': []}
    for lang, rows in pools.items():
        rows = dedupe(rows)
        random.Random(f'{SEED}:{lang}').shuffle(rows)  # noqa: S311 — reproducible shuffle
        print(f'{lang}: {len(rows)} usable')
        start = 0
        for split in ('test', 'val', 'train'):  # test first: it never depends on train's size
            n = PER_LANGUAGE[split]
            if start + n > len(rows):
                raise SystemExit(f'{lang} has too few rows for {split}')
            splits[split].extend(rows[start : start + n])
            start += n
    OUT.mkdir(parents=True, exist_ok=True)
    for split, rows in splits.items():
        random.Random(f'{SEED}:{split}').shuffle(rows)  # noqa: S311 — reproducible shuffle
        with (OUT / f'{split}.jsonl').open('w', encoding='utf-8') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        print(split, len(rows))


if __name__ == '__main__':
    main()
