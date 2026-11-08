# PocketGPT

A ChatGPT-like web chat whose model runs on the user's own computer: Qwen2.5-1.5B-Instruct,
LoRA fine-tuned on Colab for English, Russian and Uzbek, served as a GGUF by llama.cpp.
Portfolio project.

## Read first

- `docs/STATUS.md` — at the start of every session: where the project stands, the next step.
- `LEARN.md` — why each mechanism exists, trade-offs, interview Q&A. Update after each milestone.
- `docs/REPORT.uz.md` — the write-up for the user (Uzbek).

## Shape

```
backend/   FastAPI (Python 3.11, conda env `pocket`): settings, providers, SSE chat, SQLite store
web/       Next.js 16 App Router (yarn 1, port 4100): one chat page
training/  build_dataset.py (C2), train.py + train_colab.ipynb (C3), evaluate.py (C4)
data/      pocket_chat/{train,val,test}.jsonl — test is frozen
models/    GGUF files (git-ignored)
```

## Rules

- Answer the user in Uzbek; code and comments in English. Expand every abbreviation.
- Plan before non-trivial changes. No package without the problem it solves and the alternative.
- Next.js 16 differs from older versions: read `web/node_modules/next/dist/docs/` before using an API.
- Providers implement `ChatProvider.stream()`; the API never knows which model runs.
- The test split never changes. A new dataset rule rebuilds train/val only by changing the seed
  scheme deliberately — and says so in LEARN.md.
- Model files, `.env` and the SQLite database never go into git.

## Git

`main` ← `develop` ← `feature/<milestone>`. Conventional commits. No `Co-Authored-By` or other
Claude attribution. Stage files by name, read `git diff --cached`, and scan it before committing:
`git diff --cached | grep -nE "sk-or-[A-Za-z0-9_-]{10,}|sk-ant-[A-Za-z0-9_-]{10,}|hf_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}"`

## Validation

```bash
cd backend && ruff check . && ruff format --check . && pytest -q
cd web && yarn typecheck && yarn lint && yarn build
```
