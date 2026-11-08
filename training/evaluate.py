"""
C4 — evaluate a model on the frozen test set (data/pocket_chat/test.jsonl: 100 EN, 100 RU, 100 UZ).

The model is reached through any OpenAI-compatible server — llama-server with the base GGUF, or
with the fine-tuned one — so both are measured by the same code, prompt and decoding:

    llama-server -m models/<file>.gguf --port 8080 -c 4096 -ngl 99
    python training/evaluate.py --label base       # → reports/eval_base.json
    python training/evaluate.py --label tuned      # → reports/eval_tuned.json
    python training/evaluate.py --compare base tuned   # → reports/EVAL.md

Metrics (no judge model — all reproducible):
- in_language: the answer is in the question's language (the product's promise); a text with
  no language to judge (a list of names, a number) is not counted against the model;
- chrF: character n-gram F-score against the dataset's answer (0–100);
- repetition: a 4-word phrase repeated 4+ times (a looping small model);
- mean_chars: answer length.
"""

import argparse
import json
import re
import statistics
import time
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / 'data' / 'pocket_chat' / 'test.jsonl'
REPORTS = ROOT / 'reports'

UZ_MARKERS = re.compile(
    r"(o['ʻ‘’`]|g['ʻ‘’`]|\b(va|bu|uchun|bilan|ham|emas|bo'?l|qanday|nima|mumkin|kerak|edi|yoki)\b)",
    re.IGNORECASE,
)
# Uzbek suffixes English never has at a word's end (case, plural, participle, verb endings).
UZ_SUFFIXES = re.compile(
    r'\b\w{2,}(ning|lari|larni|dagi|dan|lik|gan|moqda|adi|ishi|ligi|siz|miz)\b', re.IGNORECASE
)
EN_WORDS = re.compile(r'\b(the|and|is|are|to|of|in|that|you|it|for|with|can)\b', re.IGNORECASE)


def language_of(text: str) -> str:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return '?'
    cyrillic = sum(0x0400 <= ord(ch) <= 0x04FF for ch in letters) / len(letters)
    if cyrillic > 0.5:
        return 'RU'
    words = max(1, len(text.split()))
    uz = (len(UZ_MARKERS.findall(text)) + len(UZ_SUFFIXES.findall(text))) / words
    en = len(EN_WORDS.findall(text)) / words
    if uz == en == 0:
        return '?'  # a list of names, a number: no language to judge
    return 'UZ' if uz > en else 'EN'


def char_ngrams(text: str, n: int) -> Counter:
    text = ' '.join(text.split())
    return Counter(text[i : i + n] for i in range(len(text) - n + 1))


def chrf(hypothesis: str, reference: str, max_n: int = 6, beta: float = 2.0) -> float:
    """chrF (Popović 2015): average char n-gram precision/recall, recall weighted beta=2."""
    precisions, recalls = [], []
    for n in range(1, max_n + 1):
        hyp, ref = char_ngrams(hypothesis, n), char_ngrams(reference, n)
        if not hyp or not ref:
            continue
        overlap = sum((hyp & ref).values())
        precisions.append(overlap / sum(hyp.values()))
        recalls.append(overlap / sum(ref.values()))
    if not precisions:
        return 0.0
    p, r = statistics.mean(precisions), statistics.mean(recalls)
    if p + r == 0:
        return 0.0
    return 100 * (1 + beta**2) * p * r / (beta**2 * p + r)


def loops(text: str) -> bool:
    words = text.lower().split()
    grams = Counter(tuple(words[i : i + 4]) for i in range(len(words) - 3))
    return bool(grams) and max(grams.values()) >= 4


def ask(url: str, messages: list[dict], max_tokens: int) -> str:
    body = json.dumps(
        {'messages': messages, 'max_tokens': max_tokens, 'temperature': 0, 'stream': False}
    ).encode()
    req = urllib.request.Request(  # noqa: S310 — a local llama-server, http only
        url.rstrip('/') + '/v1/chat/completions', body, {'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=300) as response:  # noqa: S310 — a local server
        return json.load(response)['choices'][0]['message']['content'] or ''


def run(label: str, url: str, limit: int, max_tokens: int) -> None:
    tests = [json.loads(line) for line in TEST.open(encoding='utf-8')]
    if limit:
        tests = tests[:limit]
    rows = []
    started = time.perf_counter()
    for index, t in enumerate(tests, 1):
        prompt, reference = t['messages'][:-1], t['messages'][-1]['content']
        answer = ask(url, prompt, max_tokens)
        rows.append(
            {
                'lang': t['lang'],
                'question': prompt[-1]['content'][:300],
                'answer': answer,
                # '?' (a list of names, a number) is not counted as a wrong language.
                'in_language': language_of(answer) in (t['lang'], '?'),
                'chrf': round(chrf(answer, reference), 2),
                'loops': loops(answer),
                'chars': len(answer),
            }
        )
        if index % 25 == 0:
            print(f'{index}/{len(tests)}', flush=True)
    summary = {
        'label': label,
        'n': len(rows),
        'minutes': round((time.perf_counter() - started) / 60, 1),
    }
    for lang in ['ALL', 'EN', 'RU', 'UZ']:
        part = [r for r in rows if lang == 'ALL' or r['lang'] == lang]
        if not part:
            continue
        summary[lang] = {
            'in_language': round(100 * statistics.mean(r['in_language'] for r in part), 1),
            'chrf': round(statistics.mean(r['chrf'] for r in part), 1),
            'repetition': round(100 * statistics.mean(r['loops'] for r in part), 1),
            'mean_chars': round(statistics.mean(r['chars'] for r in part)),
        }
    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f'eval_{label}.json'
    out.write_text(json.dumps({'summary': summary, 'rows': rows}, indent=2, ensure_ascii=False))
    print(json.dumps(summary, indent=2))
    print('written', out)


def compare(a: str, b: str) -> None:
    left = json.loads((REPORTS / f'eval_{a}.json').read_text())
    right = json.loads((REPORTS / f'eval_{b}.json').read_text())
    lines = [
        '# PocketGPT — evaluation',
        '',
        f'Frozen test set: {left["summary"]["n"]} questions (100 EN, 100 RU, 100 UZ),',
        'greedy decoding, the same system prompt as the app. Generated by `training/evaluate.py`.',
        '',
        f'| Language | Metric | {a} | {b} |',
        '| --- | --- | ---: | ---: |',
    ]
    for lang in ['ALL', 'EN', 'RU', 'UZ']:
        for metric in ['in_language', 'chrf', 'repetition', 'mean_chars']:
            before, after = left['summary'][lang][metric], right['summary'][lang][metric]
            lines.append(f'| {lang} | {metric} | {before} | {after} |')
    lines += ['', '## Uzbek samples', '']
    for l_row, r_row in list(zip(left['rows'], right['rows'], strict=True)):
        if l_row['lang'] != 'UZ':
            continue
        lines += [
            f'**{l_row["question"][:160]}**',
            '',
            f'- {a}: {l_row["answer"][:300]}',
            f'- {b}: {r_row["answer"][:300]}',
            '',
        ]
        if sum(1 for line in lines if line.startswith('**')) >= 6:
            break
    (REPORTS / 'EVAL.md').write_text('\n'.join(lines) + '\n')
    print('written', REPORTS / 'EVAL.md')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', default='base')
    parser.add_argument('--url', default='http://127.0.0.1:8080')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--max-tokens', type=int, default=256)
    parser.add_argument('--compare', nargs=2, metavar=('A', 'B'))
    args = parser.parse_args()
    if args.compare:
        compare(*args.compare)
    else:
        run(args.label, args.url, args.limit, args.max_tokens)


if __name__ == '__main__':
    main()
