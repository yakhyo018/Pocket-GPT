# Status

_Last updated: 2026-11-08 — C1, C2, C5, C6 done; C3 code ready (smoke-tested on a Mac), the Colab run
is the user's step; C4 has the base model's numbers. Nothing pushed (no GitHub repository yet)._

## Done

- **C1** FastAPI app factory, `/health`, `POST /v1/chat` (stateless SSE), CORS for the web origin
  only, Next.js 16 chat page, GitHub Actions (backend ruff + pytest, web typecheck + lint + build).
- **C5** `llama.cpp` (brew) + `models/qwen2.5-1.5b-instruct-q4_k_m.gguf` (1.1 GB, git-ignored);
  `OpenAICompatProvider` for llama-server and OpenRouter.
- **C6** conversations in SQLite (`backend/data/pocket.db`), Stop saves the partial reply,
  context window fitting, Markdown via react-markdown, OpenRouter provider.
- **C2** `training/build_dataset.py` → `data/pocket_chat` 3,600 / 150 / 300 (EN/RU/UZ equal).
- **C3** `training/train.py` (smoke run on a Mac: Qwen2.5-0.5B, 40 rows, 5 steps, save + merge OK)
  and `training/train_colab.ipynb` (QLoRA on a T4 + GGUF export).
- **C4** `training/evaluate.py`; `reports/eval_base.json`.

Checked: backend pytest 21 passed, ruff clean; web typecheck, lint, build; in the browser —
desktop and phone, streaming, Stop (llama-server logged `cancel task`), saved conversations.

## The user's steps

1. Create the GitHub repository and push (`main`), so Colab can clone it.
2. Colab: open `training/train_colab.ipynb`, T4 runtime, Run all (~40–60 min); download the GGUF.
3. Put it in `models/`, restart llama-server with it, run
   `python training/evaluate.py --label tuned && python training/evaluate.py --compare base tuned`.

## Open

- GGUF conversion was not run on the Mac (running llama.cpp's scripts locally was not allowed in the
  session); it runs in the notebook.
- On a phone the conversation list is hidden (only "New chat").
- No login: a single local user. Do not expose the backend to the internet as it is.
