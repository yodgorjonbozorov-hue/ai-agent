# Disney Navoiy — Hisobot Bot

Ishchi guruhlardan kunlik ish hisobotlarini avtomatik so'raydigan, yig'adigan
va adminga xulosa beradigan Telegram bot.

> **Holat:** 3-bosqich yakunlandi. systemd unit, VPS yo'riqnomasi va debug
> komandalar 4-bosqichда qo'shiladi.

## Texnologiyalar

- Python 3.11+
- [aiogram 3.x](https://docs.aiogram.dev/) — asinxron Telegram bot
- [APScheduler](https://apscheduler.readthedocs.io/) — kunlik jadval
- SQLite + `aiosqlite` — ma'lumotlar bazasi
- Anthropic Claude API — AI tekshiruv (2-bosqich)
- Vaqt mintaqasi: `Asia/Tashkent` (`zoneinfo`)

## Loyiha strukturasi

```
.
├── bot.py                 # kirish nuqtasi
├── config.py              # .env o'qish, log sozlash
├── database.py            # baza sxemasi va CRUD
├── texts.py               # o'zbekcha matn shablonlari
├── handlers/
│   ├── admin.py           # admin komandalari (shaxsiy chat)
│   └── groups.py          # guruh xabarlari va my_chat_member
├── services/
│   ├── scheduler.py       # kunlik jadval joblari
│   └── reporter.py        # kunlik xulosa tuzish
├── requirements.txt
├── .env.example
└── disney-bot.service     # (4-bosqichда)
```

## Hozircha nima ishlaydi

**1-bosqich**
- **Ro'yxatga olish:** bot guruhga qo'shilganda avtomatik bazaga yoziladi va
  admin xabardor qilinadi (`my_chat_member`).
- **09:00 — ertalabki xabar:** bugungi vazifalar guruhga yuboriladi
  (vazifa yo'q bo'lsa umumiy eslatma).
- **18:00 — hisobot so'rovi:** guruhга standart shablon yuboriladi.
- **Hisobot qabul qilish:** so'rovdan keyin kelgan, 50 belgidan uzun matn
  hisobot sifatida bazaga `pending` holatida yoziladi. Qisqa xabarlar
  (`ok`, `rahmat`) e'tiborsiz qoladi.
- **22:00 — kunlik xulosa:** adminga kim hisobot berdi / bermadi ko'rinishida.
- **Admin komandalari:** `/start`, `/guruhlar`, `/hisobot`, `/test_xulosa`.

**2-bosqich (AI tekshiruv)**
- **`ai_checker.py`:** har bir hisobot `claude-sonnet-4-6` modeliga yuboriladi;
  model faqat JSON qaytaradi (`toliq`, `yetishmagan`, `muammo_bormi`,
  `muammo_qisqacha`, `baho` 1–5, `qisqa_xulosa`).
- **Qayta so'rash:** to'liq bo'lmasa guruhga "…{yetishmagan} qismi yo'q —
  to'ldirib yuborasizmi?" deyiladi, status `incomplete`.
- **Qabul:** to'liq bo'lsa "✅ Hisobot qabul qilindi", status `accepted`.
- **Muammo signali:** `muammo_bormi: true` bo'lsa adminга darhol alohida xabar.
- **Xulosa boyitildi:** 22:00 xulosaga AI qisqa xulosasi va e'tibor talab
  qiladigan bandlar qo'shildi.
- **Barqarorlik:** AI kritik yo'l EMAS — timeout, rate limit yoki JSON parse
  xatosida hisobot `pending` holatida saqlanadi va bot ishlashda davom etadi.

**3-bosqich (eslatma, admin komandalari, haftalik tahlil)**
- **18:30 — 1-eslatma:** faqat hali hisobot yubormagan guruhlarga, muloyim.
- **20:00 — 2-eslatma + eskalatsiya:** guruhlarga takroriy eslatma, adminга
  "javob bermaganlar" ro'yxati.
- **Shanba 20:00 — haftalik tahlil:** har guruhning hisobot berish foizi,
  o'rtacha AI bahosi, takrorlanuvchi muammolar va intizom reytingi (🥇🥈🥉).
- **To'liq admin komandalari:**
  - `/vazifa` — interaktiv: guruh tanlash (inline keyboard) → vazifa matni (FSM)
  - `/vaqt` — interaktiv: guruh → maydon (so'rov/ertalab) → yangi vaqt; job
    avtomatik qayta rejalashtiriladi
  - `/pauza <id>` / `/faol <id>` — guruhni to'xtatish / qayta yoqish (joblar
    bilan birga)
  - `/matn <id>` — guruhning bugungi to'liq hisobot matni
  - `/haftalik` — haftalik reytingni darhol ko'rish
  - `/bekor` — interaktiv jarayonni bekor qilish

## O'rnatish (lokal test)

```bash
# 1. Bog'liqliklar
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Sozlamalar
cp .env.example .env
#   .env ni to'ldiring: BOT_TOKEN, ADMIN_ID, ANTHROPIC_API_KEY
#   (ANTHROPIC_API_KEY bo'sh bo'lsa AI tekshiruv o'chadi, bot baribir ishlaydi)

# 3. Ishga tushirish
python bot.py
```

Bot ishga tushgach:
1. Botni ishchi guruhga admin sifatida qo'shing → guruh avtomatik ro'yxatga olinadi.
2. Admin bilan shaxsiy chatда `/start` yuboring → yordam matni.
3. `/guruhlar` — ro'yxatni ko'ring.

## Sozlamalar (`.env`)

| O'zgaruvchi | Izoh |
|---|---|
| `BOT_TOKEN` | BotFather'dan olingan token |
| `ANTHROPIC_API_KEY` | Claude API kaliti (bo'sh bo'lsa AI o'chadi) |
| `ADMIN_ID` | Admin Telegram ID (butun son) |
| `DB_PATH` | Baza fayli, standart `data/bot.db` |
| `TIMEZONE` | Vaqt mintaqasi, standart `Asia/Tashkent` |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

## Keyingi bosqichlar

- **4-bosqich:** `disney-bot.service` (systemd), VPS o'rnatish yo'riqnomasi,
  qo'lda test uchun debug komandalar.
