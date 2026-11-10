# LEARN — PocketGPT

## Starting point: Jaydari GPT (reviewed 2026-11-08)

`~/Desktop/Jaydari_RAG/jaydari_gpt` is a LoRA adapter on TinyLlama-1.1B-Chat: r=8 on `q_proj` /
`v_proj` only (2.2 MB), 2 epochs, 3,500 steps of batch 1, loss 1.49 → 1.15, **no validation set**,
**no dataset or training code** in the repository. Asked the same questions, base and adapter answered
almost identically in English; both answered Russian in English ("My name is Sarah, 25…"); the
adapter's Uzbek was nonsense. Lessons kept here: train code and data live in the repo, a frozen test
set and a base-vs-tuned comparison prove the change, and the target languages are in the data.

## C1 — Skeleton (2026-11-08)

- **App factory** (`create_app(settings, provider)`): tests build their own app with the fake
  provider and an in-memory SQLite; importing the module connects nothing.
- **Provider interface** (`ChatProvider.stream()`): fake, llama.cpp and OpenRouter are settings, not
  code paths. The API and the UI never know which model runs.
- **Server-Sent Events from a POST.** `EventSource` only does GET, so the browser reads the
  response body with a stream reader and splits it on blank lines. Each piece is an
  `event: delta` with JSON; the end is `event: done` with timings.
- **Stop = closing the connection.** `AbortController.abort()` closes the fetch; Starlette cancels
  the generator; httpx closes its stream to llama-server, which logs `cancel task`. Generation
  really stops — the GPU is not left writing for nobody.
- **CORS** allows only the web origin; no credentials are sent cross-origin.

## C5 — The model on a laptop (2026-11-08)

- **GGUF + llama.cpp, not transformers.** A 1.5B model in float16 is ~3 GB and slow on an 8 GB
  Mac; the Q4_K_M GGUF is 1.1 GB and runs on Metal. First token in 65–570 ms, a short reply < 1 s.
- **One client for two servers.** llama-server and OpenRouter both speak OpenAI's
  `/v1/chat/completions` with `stream: true`, so `OpenAICompatProvider` serves both.
- **Base model, before fine-tuning:** EN correct, RU correct, UZ grammatical-looking nonsense —
  the reason for C2–C4.

## C6 — Conversations (2026-11-08)

- **SQLite from the standard library**: one local user, two tables; an ORM or a database server
  would add nothing. One connection guarded by a lock (FastAPI calls it from several threads).
- **The user's message is saved before the model runs**; the reply when it ends — or, after Stop,
  with what was written and `stopped = 1`.
- **Fitting the context window.** System prompt + the newest turns that fit
  `context_tokens − max_new_tokens`, oldest dropped first; never a window that starts with an
  assistant turn. Tokens are estimated (3 characters per token — safe for Cyrillic and Uzbek)
  because the backend does not load the tokenizer.
- **Markdown without HTML injection.** `react-markdown` renders the model's Markdown and ignores raw
  HTML by default; `dangerouslySetInnerHTML` would let a model's output run script in the page.

## C2 — Dataset (2026-11-08)

- 1,200 / 50 / 100 per language (train / val / test). Russian is the limit: Aya has ~340 usable
  rows, OASST2 adds ~1,140 (first turns, best-ranked reply).
- **The test split is drawn first** from a fixed seed, so it never depends on how much train data
  there is — a later, bigger train set does not leak test questions.
- **Train like you serve:** every example carries the app's own system prompt.
- Licences: Aya, OASST2 and the Uzbek set are Apache-2.0 → redistributable with attribution
  (`data/README.md`).

## C3 — Training (2026-11-08)

- **QLoRA on Colab's T4**: the frozen base in 4-bit NF4, LoRA r=16 on every linear layer
  (attention + MLP), loss on the reply only (prompt–completion format), validation loss every
  50 steps. T4 has no bf16 → fp16 compute.
- **One script, two machines.** `training/train.py` runs on Colab (`--qlora`) and on a Mac (float32,
  `--limit 40 --max-steps 5`): the Mac smoke test checked the data format, TRL config, save and merge
  before any GPU time was spent.
- **GGUF happens in Colab** (`convert_hf_to_gguf.py` → `llama-quantize Q4_K_M`); running llama.cpp's
  scripts on the laptop was not allowed in this session, so that path is unverified locally.

## C4 — Evaluation (2026-11-08)

- Same server, prompt and greedy decoding for base and tuned; only the GGUF changes.
- **in_language** (the product's promise) by script + Uzbek markers and suffixes; checked on the
  test set's own reference answers first (97–99 %) — a metric is tested before it judges a model.
  Texts with no language (a list of names) are not counted as wrong.
- **chrF** (character n-gram F-score) against the reference: robust to Uzbek morphology, where
  word-level overlap fails. **repetition**: a 4-word phrase 4+ times — how small models break.

## C3/C4 — The Colab run and the result (2026-11-10)

- **Run:** Qwen2.5-1.5B-Instruct, QLoRA r=16, 1 epoch, 225 steps, 132.5 min on a T4. Validation loss
  1.791 → 1.754 → 1.732 → 1.722 → 1.722 (steps 50–225); token accuracy 58 % → 62 %. The same
  numbers in two runs (`seed=42`): the run is reproducible.
- **Three things broke on Colab, each fixed in code, not by hand:** the T4 (compute capability 7.5)
  cannot run TRL's fp32-output matmul → its fallback is switched on; Colab's torchao 0.10 made PEFT
  refuse to merge → uninstalled; a runtime reset wiped `/content` twice (once after a finished run)
  → the adapter, checkpoints (every 25 steps, with optimizer state) and the GGUF live on Google
  Drive, and a rerun resumes or skips training.
- **Result on the frozen 300-question test** (`reports/EVAL.md`): repetition 12.7 % → 4.0 %
  (Uzbek 23 % → 9 %), chrF 27.1 → 30.8 (Uzbek 26.9 → 32.7), in-language 97.0 → 97.3 (English
  98 → 96, the one metric that dropped).
- **Three hand-picked questions misled.** In the notebook the tuned model looked worse in Uzbek; the
  300-question test says it is clearly better. A few samples show the failure modes; only the full
  test says which way the model moved.
- **What did not change: facts.** Uzbek answers are fluent more often but still invent dates and
  names — LoRA on 1,200 machine-translated chats teaches form, not knowledge. A bigger base (7B on
  an L4/A100) or RAG would be the next step for facts.

## UI polish for the portfolio (2026-11-10)

- **One dark theme, colours as CSS variables.** A light theme later is one more `:root` block, not a
  rewrite. Mockups were rendered to PNG first (static HTML + headless Chrome) and the user picked
  the dark one before any app code changed.
- **No new packages.** Icons are a dozen inline SVGs (`components/icons.tsx`); an icon library
  would ship hundreds for twelve. Inter comes from `next/font/google`, which downloads the font at
  build time and serves it from our origin — the visitor's browser never calls Google.
- **Code blocks get a header and Copy** by overriding react-markdown's `pre` component; the
  language comes from the `language-x` class react-markdown puts on `<code>`.
- **The model's name comes from the backend:** `/health` returns `model` (`POCKET_MODEL_LABEL`),
  so the web app never hard-codes which GGUF runs.
- **Never read the clock during render.** Next.js prerenders the page; `new Date()` in a Client
  Component is evaluated at build time and frozen into the HTML (Next 16 reports it as an error).
  The "Today / Yesterday" grouping takes `now` when the list is fetched, in an effect.
- **Phone:** the sidebar is a drawer (CSS `transform` + a scrim), so conversations are reachable on
  a phone — the open item from C6.

## Interview questions

1. Why stream with SSE and not WebSockets? One direction (server → browser) over plain HTTP —
   proxies, CORS and retries just work; WebSockets add a protocol for nothing here.
2. How does Stop stop the GPU, not just the screen? Closing the connection cancels the server's
   generator, which closes the upstream stream; llama.cpp cancels the task.
3. Why a frozen test set, drawn first? Comparable numbers across runs, and no leak into training.
4. Why QLoRA? A 4-bit base cuts memory ~4×, so a 1.5B model trains on a free 16 GB T4; only the
   adapter is in 16-bit and trained.
5. Why chrF instead of BLEU for Uzbek? Agglutinative words share stems but not whole words;
   character n-grams credit them.
6. How do you survive a preemptible GPU? Checkpoint to persistent storage (adapter + optimizer +
   scheduler + RNG state) and make the job idempotent: rerun → resume or skip.
7. Why did three samples disagree with the test set? Small samples show anecdotes; a fixed test set
   measures the direction. Decide on the set, illustrate with samples.
8. Why must `new Date()` not run in render in Next.js? The page is prerendered at build time; the
   value would be the build's time, and server and browser would disagree (hydration mismatch).
   Read the clock in an effect or event handler.
