# PocketGPT — hisobot (2026-11-08)

## 1. Bu nima

**PocketGPT** — ChatGPT'ga o'xshash veb chat, lekin model **sizning kompyuteringizda** ishlaydi.
- **Model:** `Qwen2.5-1.5B-Instruct`, Google Colab'da LoRA bilan **ingliz, rus va o'zbek** tillariga moslashtiriladi.
- **Ishga tushirish:** 1 GB'lik GGUF fayl sifatida `llama.cpp` orqali Mac'ning GPU'sida (Metal) ishlaydi.
- **Repo:** `~/Desktop/pocket-gpt`. Lokal commit qilingan, GitHub'ga hali yuklanmagan.

## 2. Jaydari GPT'dan nima o'rgandik

| Jaydari GPT | PocketGPT |
| --- | --- |
| TinyLlama 1.1B, asosan ingliz tilida | Qwen2.5 1.5B, ko'p tilli (rus tilini yaxshi biladi) |
| LoRA r=8, faqat `q_proj` va `v_proj`; adapter 2.2 MB | LoRA r=16, barcha chiziqli qatlamlar (attention va MLP) |
| Validatsiya yo'q | Har 50 qadamda validatsiya loss |
| Dataset va o'qitish kodi repo'da **yo'q** | Dataset, `train.py` va Colab notebook repo'da |
| Base model bilan solishtirilmagan | Qotirilgan 300 ta test savoli, base va tuned bir xil kod bilan o'lchanadi |
| Sinov: ruscha savolga inglizcha javob, o'zbekchasi ma'nosiz | Til dataset'ga ataylab qo'shilgan: har tildan 1 200 tadan |

## 3. Arxitektura

```
Brauzer (Next.js 16, :4100)
   │  POST /v1/conversations/{id}/messages          ← SSE: delta, delta, …, done
   ▼
Backend (FastAPI, :8200) ── SQLite (suhbatlar)
   │  OpenAI'ga mos /v1/chat/completions, stream
   ▼
llama-server (:8080, Metal) ── models/*.gguf        (yoki OpenRouter, xuddi shu API)
```

**Ilova imkoniyatlari:**
- javob token-token oqib chiqadi (SSE, Server-Sent Events);
- **"Stop" tugmasi** generatsiyani server'da haqiqatan to'xtatadi: `llama-server` logida `cancel task` yozuvi chiqadi. Yozilgan qism `stopped` belgisi bilan saqlanadi;
- suhbatlar tarixi: ro'yxat, yangi suhbat, o'chirish;
- kontekst oynasi: suhbat uzaysa, eng eski xabarlar tashlanadi, system prompt va oxirgi savol doim qoladi;
- Markdown ko'rinishi `react-markdown` orqali, xom HTML bloklangan (XSS'dan himoya);
- provider sozlamada tanlanadi: `fake` (testlar uchun), `llamacpp` yoki `openrouter`.

## 4. Bosqichlar

**C1 — skelet.** FastAPI app factory, `/health`, SSE chat, faqat web manzili uchun CORS, Next.js sahifasi, CI (backend: ruff + pytest; web: typecheck + lint + build).

**C5 — lokal model.**
- `brew install llama.cpp` va Qwen'ning rasmiy Q4_K_M GGUF fayli (1.1 GB).
- Birinchi token 65–570 ms ichida keladi, qisqa javob 1 soniyagacha.

**C6 — suhbatlar.**
- SQLite standart kutubxona orqali: bitta foydalanuvchi, ikkita jadval, ORM kerak emas.
- Kontekstni qisqartirish uchun tokenlar taxminan sanaladi: 3 belgi ≈ 1 token. Bu rus va o'zbek tillari uchun xavfsiz chegara.

**C2 — dataset** (`data/pocket_chat`):
- train 3 600, validatsiya 150, **qotirilgan test 300**; har tildan teng.
- Manbalar, uchalasi ham Apache-2.0 litsenziyali: `CohereLabs/aya_dataset` (EN, RU), `OpenAssistant/oasst2` (RU), `UAzimov/uzbek-instruct-llm` (UZ).
- Test birinchi bo'lib ajratiladi. Shuning uchun keyin train hajmi o'zgarsa ham, test savollari o'qitishga aralashmaydi.

**C3 — o'qitish.**
- `training/train.py`: Colab T4'da QLoRA, ya'ni base model 4-bit NF4 formatida, ustida LoRA r=16. Loss faqat javob qismidan hisoblanadi.
- Kod Mac'da kichik model bilan sinaldi: Qwen 0.5B, 40 misol, 5 qadam. Saqlash va merge ishladi.
- `training/train_colab.ipynb`: o'qitish, base va tuned'ni solishtirish, GGUF'ga o'tkazish va yuklab olish.

**C4 — baholash** (`training/evaluate.py`). Bir xil server, prompt va greedy dekodlash ishlatiladi, faqat GGUF fayli almashadi.
- `in_language` — savol tilida javob berildimi. Aniqlagich avval testdagi **namunaviy javoblarning o'zida** sinaldi: 97–99% to'g'ri.
- `chrF` — belgilar n-gramm o'xshashligi. O'zbek tilining qo'shimchali tuzilishi uchun so'z darajasidagi metrikalardan adolatliroq.
- `repetition` — 4 so'zli ibora 4 martadan ko'p takrorlanganmi.

## 5. Natijalar: base model (fine-tune'dan oldin)

| Til | Savol tilida | chrF | Takrorlanish | O'rtacha uzunlik |
| --- | ---: | ---: | ---: | ---: |
| EN | 98.0% | 30.1 | 3.0% | 460 |
| RU | 98.0% | 24.3 | 12.0% | 426 |
| **UZ** | 95.0% | 26.9 | **23.0%** | 283 |
| Hammasi | 97.0% | 27.1 | 12.7% | 390 |

**Xulosa.** Qwen 1.5B, TinyLlama'dan farqli o'laroq, system prompt yordamida deyarli doim to'g'ri tilda javob beradi. **O'zbekchadagi muammo — sifat:** har to'rtinchi javob takrorlanishga tushib qoladi, faktlar ham ko'pincha noto'g'ri. Masalan, "O'zbekistonning poytaxti qayer?" savoliga base model ma'nosiz javob berdi. Fine-tune'dan kutilgan natija: o'zbekchada takrorlanish kamayishi va chrF oshishi. Buni Colab'dan keyin `evaluate.py --compare base tuned` ko'rsatadi.

## 6. Sizning qadamlaringiz

1. **GitHub.** Repo yarating, masalan `yakhyo018/pocket-gpt`. Keyin:
   ```bash
   cd ~/Desktop/pocket-gpt && git remote add origin https://github.com/yakhyo018/pocket-gpt.git && git push -u origin main
   ```
2. **Colab.** `training/train_colab.ipynb` ni oching, Runtime'ni **T4 GPU** qiling va *Run all* bosing (~40–60 daqiqa). Repo private bo'lsa, Colab Secrets'ga `GITHUB_TOKEN` qo'shing.
3. **Mac.** Yuklab olingan `pocketgpt-1.5b-q4_k_m.gguf` faylini `models/` papkasiga qo'ying, keyin:
   ```bash
   llama-server -m models/pocketgpt-1.5b-q4_k_m.gguf --port 8080 -c 4096 -ngl 99
   ```
   ```bash
   cd ~/Desktop/pocket-gpt && python3 training/evaluate.py --label tuned && python3 training/evaluate.py --compare base tuned
   ```

## 7. Halol cheklovlar

- **GGUF konvertatsiyasi Mac'da sinalmagan.** Bu sessiyada `llama.cpp` skriptlarini lokal ishga tushirishga ruxsat berilmadi. Konvertatsiya notebook ichida bajariladi.
- **O'zbekcha dataset asosan mashina tarjimasi** (Dolly'ga o'xshash). Model tarjimaga xos uslubni ham o'rganishi mumkin.
- **1.5B model ChatGPT emas**, ayniqsa faktlarda. Maqsad aniq o'lchanadigan yaxshilanish.
- **Login yo'q.** Bitta lokal foydalanuvchi uchun. Backend'ni internetga shu holida ochib bo'lmaydi.
- **Telefonda suhbatlar ro'yxati yashirin**, faqat "New chat" tugmasi bor.

## 8. Intervyu savollari

1. Nega SSE, WebSocket emas? Ma'lumot bir yo'nalishda oqadi, oddiy HTTP yetarli, proxy va CORS muammosiz ishlaydi.
2. "Stop" GPU'ni qanday to'xtatadi? Ulanish yopilganda server'dagi generator bekor qilinadi, u `llama-server` bilan ulanishni yopadi, `llama-server` esa vazifani bekor qiladi.
3. Nega test to'plami birinchi va qotirilgan? Natijalarni solishtirish mumkin bo'ladi va test savollari o'qitishga sizib kirmaydi.
4. QLoRA nima beradi? 4-bit base xotirani taxminan 4 marta kamaytiradi. 1.5B model bepul 16 GB T4'ga sig'adi, faqat adapter o'qitiladi.
5. Nega o'zbek tili uchun chrF, BLEU emas? Qo'shimchali tilda so'zlar o'zakda mos keladi, lekin to'liq so'z sifatida mos kelmaydi. Belgilar n-grammlari buni hisobga oladi.
6. Nega transformers emas, `llama.cpp` + GGUF? 1.5B model fp16'da 3 GB va 8 GB Mac'da sekin ishlaydi. Q4 formatda 1.1 GB va Metal'da 1 soniyagacha javob beradi.
