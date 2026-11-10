# PocketGPT

A ChatGPT-like web chat whose model runs **on your own computer**: Qwen2.5-1.5B-Instruct,
LoRA fine-tuned on Google Colab for **English, Russian and Uzbek**, served as a 1 GB GGUF by llama.cpp.

| Milestone | | Status |
| --- | --- | --- |
| C1 | Skeleton — FastAPI, SSE streaming, Next.js chat page, CI | ✅ |
| C2 | Dataset — 3,600 / 150 / 300 chats (EN/RU/UZ, Apache-2.0 sources), frozen test | ✅ |
| C3 | Fine-tune — `training/train.py` + Colab notebook (QLoRA on a T4, 132 min) | ✅ |
| C4 | Evaluation — in-language rate, chrF, repetition; base vs tuned | ✅ |
| C5 | Local model — llama.cpp + GGUF, OpenAI-compatible provider | ✅ (tuned GGUF) |
| C6 | Chat app — conversations (SQLite), Stop, context window, Markdown, OpenRouter | ✅ |

Frozen test set, 300 questions (EN/RU/UZ), base → tuned ([`reports/EVAL.md`](reports/EVAL.md)):

| | in the question's language | chrF | repetition |
| --- | ---: | ---: | ---: |
| All | 97.0 → 97.3 % | 27.1 → **30.8** | 12.7 → **4.0 %** |
| Uzbek | 95 → 97 % | 26.9 → **32.7** | 23 → **9 %** |

The fine-tune fixed fluency (repetition down 3×), not facts: a 1.5B model still invents Uzbek dates
and names.
Write-up (Uzbek): [`docs/REPORT.uz.md`](docs/REPORT.uz.md)

## Architecture

```
web (Next.js, :4100) ──POST /v1/conversations/{id}/messages──▶ backend (FastAPI, :8200)
        ▲                                                         │ SQLite: conversations
        └──────────── text/event-stream: delta… done ◀────────────┤
                                                                  ▼
                                    llama-server (:8080, Metal) ── models/*.gguf
                                    or OpenRouter (same OpenAI-compatible API)
```

## Run

```bash
brew install llama.cpp
llama-server -m models/qwen2.5-1.5b-instruct-q4_k_m.gguf --port 8080 -c 4096 -ngl 99
```

```bash
conda create -n pocket python=3.11 && conda activate pocket
cd backend && pip install -e '.[dev]' && cp .env.example .env && pocket-api      # :8200
```

```bash
cd web && yarn install && yarn dev                                                # :4100
```

The base GGUF: `Qwen/Qwen2.5-1.5B-Instruct-GGUF` → `qwen2.5-1.5b-instruct-q4_k_m.gguf` into `models/`.
After Colab: `models/pocketgpt-1.5b-q4_k_m.gguf`, then restart `llama-server` with it.

## Train (Colab) and evaluate

1. Push this repository to GitHub, open `training/train_colab.ipynb` in Colab, T4 runtime, Run all.
2. Download `pocketgpt-1.5b-q4_k_m.gguf` into `models/`, restart `llama-server` with it.
3. `python training/evaluate.py --label tuned && python training/evaluate.py --compare base tuned`

## Checks

```bash
cd backend && ruff check . && ruff format --check . && pytest -q
cd web && yarn typecheck && yarn lint && yarn build
```
