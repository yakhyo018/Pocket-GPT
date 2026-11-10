# Status

_Last updated: 2026-11-10 — C1–C6 done. The Colab run (QLoRA, 132 min on a T4) finished; the tuned
GGUF runs locally and beats the base on the frozen test (repetition 12.7 → 4.0 %, chrF 27.1 → 30.8).
Pushed to github.com/yakhyo018/Pocket-GPT (`main`)._

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

- **C3 run** on Colab: 225 steps, validation loss 1.791 → 1.722; adapter, checkpoints and GGUF on
  Google Drive (`MyDrive/pocket-gpt`). `models/pocketgpt-1.5b-q4_k_m.gguf` (941 MB, git-ignored).
- **C4** `reports/EVAL.md`, `reports/eval_tuned.json`.

## Next (optional)

- Facts in Uzbek: a bigger base (Qwen2.5-7B on an L4/A100) or retrieval; DPO against repetition.

## Open

- GGUF conversion runs only in the notebook (llama.cpp's scripts were not run on the Mac).
- English in-language rate dropped 98 → 96 %; Uzbek answers still contain invented facts.
- On a phone the conversation list is hidden (only "New chat").
- No login: a single local user. Do not expose the backend to the internet as it is.
