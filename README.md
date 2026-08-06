# Disney Navoiy — Hisobot Bot

Ishchi guruhlardan kunlik ish hisobotlarini avtomatik so'raydigan, yig'adigan
va adminga xulosa beradigan Telegram bot.

> **Holat:** 1-bosqich yakunlandi. AI tekshiruv, eslatma/eskalatsiya,
> to'liq admin komandalari va haftalik tahlil keyingi bosqichlarда qo'shiladi.

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

## 1-bosqichда nima ishlaydi

- **Ro'yxatga olish:** bot guruhga qo'shilganda avtomatik bazaga yoziladi va
  admin xabardor qilinadi (`my_chat_member`).
- **09:00 — ertalabki xabar:** bugungi vazifalar guruhga yuboriladi
  (vazifa yo'q bo'lsa umumiy eslatma).
- **18:00 — hisobot so'rovi:** guruhга standart shablon yuboriladi.
- **Hisobot qabul qilish:** so'rovdan keyin kelgan, 50 belgidan uzun matn
  hisobot sifatida bazaga `pending` holatida yoziladi. Qisqa xabarlar
  (`ok`, `rahmat`) e'tiborsiz qoladi.
- **22:00 — kunlik xulosa:** adminga kim hisobot berdi / bermadi ko'rinishida
  (hozircha AI'siz).
- **Admin komandalari:** `/start`, `/guruhlar`, `/hisobot`, `/test_xulosa`.

## O'rnatish (lokal test)

```bash
# 1. Bog'liqliklar
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Sozlamalar
cp .env.example .env
#   .env ni to'ldiring: BOT_TOKEN, ADMIN_ID (ANTHROPIC_API_KEY 2-bosqichda kerak)

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
| `ANTHROPIC_API_KEY` | Claude API kaliti (2-bosqich) |
| `ADMIN_ID` | Admin Telegram ID (butun son) |
| `DB_PATH` | Baza fayli, standart `data/bot.db` |
| `TIMEZONE` | Vaqt mintaqasi, standart `Asia/Tashkent` |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

## Keyingi bosqichlar

- **2-bosqich:** `ai_checker.py` — Claude orqali hisobotni baholash, to'ldirishni
  so'rash, muammolarni darhol adminга yuborish.
- **3-bosqich:** 18:30 va 20:00 eslatma/eskalatsiya, to'liq admin komandalari,
  haftalik tahlil.
- **4-bosqich:** `disney-bot.service` (systemd), VPS o'rnatish yo'riqnomasi,
  debug komandalar.
