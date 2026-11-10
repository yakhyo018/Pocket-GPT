# PocketGPT — hisobot (2026-11-10)

## 1. Bu nima

**PocketGPT** — ChatGPT'ga o'xshash veb chat, lekin model **sizning kompyuteringizda** ishlaydi.
- **Model:** `Qwen2.5-1.5B-Instruct`, Google Colab'da LoRA bilan **ingliz, rus va o'zbek** tillariga moslashtiriladi.
- **Ishga tushirish:** 1 GB'lik GGUF fayl sifatida `llama.cpp` orqali Mac'ning GPU'sida (Metal) ishlaydi.
- **Repo:** `~/Desktop/pocket-gpt`, GitHub: [yakhyo018/Pocket-GPT](https://github.com/yakhyo018/Pocket-GPT).

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

## 6. Natijalar: fine-tune'dan keyin (2026-11-10)

**O'qitish.** Colab T4'da 132.5 daqiqa, 225 qadam. Validatsiya loss 1.791 dan 1.722 ga tushdi, keyingi tokenni to'g'ri topish 58% dan 62% ga oshdi. Ikki marta o'qitilganda raqamlar bir xil chiqdi (`seed=42`).

**Qotirilgan 300 ta savol** (`reports/EVAL.md`):

| Til | Savol tilida | chrF | Takrorlanish |
| --- | ---: | ---: | ---: |
| EN | 98 → 96% | 30.1 → 32.6 | 3 → **0%** |
| RU | 98 → 99% | 24.3 → 27.2 | 12 → **3%** |
| **UZ** | 95 → 97% | 26.9 → **32.7** | 23 → **9%** |
| Hammasi | 97.0 → 97.3% | 27.1 → **30.8** | 12.7 → **4.0%** |

**Xulosa:**
- Takrorlanish 3 marta kamaydi, chrF hamma tilda oshdi. Fine-tune aynan maqsad qilingan muammoni hal qildi.
- **Faktlar o'zgarmadi.** O'zbekcha javoblar ravonroq bo'ldi, lekin model sanalar va nomlarni hamon to'qib chiqaradi. LoRA javob shaklini o'rgatadi, bilim bermaydi.
- **Bitta ko'rsatkich tushdi:** inglizcha savollarga savol tilida javob berish 98% dan 96% ga.
- **Saboq:** notebook'dagi 3 ta savolda tuned model o'zbekchada yomonroq ko'ringan edi. 300 ta savolli test esa aniq yaxshilanishni ko'rsatdi. Bir nechta misol faqat xato turlarini ko'rsatadi, model qaysi tomonga o'zgarganini to'liq test aytadi.

**Colab'dagi uchta muammo va ularning yechimi:**
1. T4 TRL'ning fp32 chiqishli ko'paytirishini qo'llamaydi → TRL'ning zaxira yo'li yoqildi.
2. Colab'dagi eski torchao 0.10 tufayli PEFT merge qilishdan bosh tortdi → torchao o'chirildi.
3. Runtime ikki marta uzilib, `/content` o'chib ketdi → adapter, checkpoint'lar (har 25 qadamda) va GGUF endi Google Drive'da saqlanadi. Qayta ishga tushirilganda o'qitish davom etadi yoki o'tkazib yuboriladi.

## 7. Halol cheklovlar

- **GGUF faqat notebook ichida yaratiladi.** `llama.cpp` skriptlari Mac'da ishga tushirilmagan.
- **Faktlar:** 1.5B model o'zbekchada faktlarni to'qiydi. Keyingi qadam: kattaroq base model (7B) yoki RAG.
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
7. Bir nechta misol va to'liq test qarama-qarshi natija bersa, qaysi biriga ishonish kerak? Qotirilgan to'liq testga. Misollar faqat xato turlarini ko'rsatish uchun ishlatiladi.
8. Bepul GPU uzilib qolsa, qanday himoyalanish mumkin? Checkpoint'ni doimiy xotiraga yozish (adapter, optimizer, scheduler va RNG holati bilan) va job'ni idempotent qilish: qayta ishga tushirilganda davom etadi yoki o'tkazib yuboradi.
