# Disney Navoiy — Hisobot Bot

Ishchi guruhlardan kunlik ish hisobotlarini avtomatik so'raydigan, yig'adigan
va adminga xulosa beradigan Telegram bot.

> **Holat:** To'liq tayyor (1–4 bosqich). systemd bilan VPS'да ishga tushirishga
> tayyor.

## Texnologiyalar

- Python 3.11+
- [aiogram 3.x](https://docs.aiogram.dev/) — asinxron Telegram bot
- [APScheduler](https://apscheduler.readthedocs.io/) — kunlik jadval
- SQLite + `aiosqlite` — ma'lumotlar bazasi
- Anthropic Claude API — AI tekshiruv (`claude-sonnet-4-6`)
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
│   ├── ai_checker.py      # Claude API orqali hisobotni baholash
│   ├── scheduler.py       # kunlik jadval joblari
│   └── reporter.py        # kunlik/haftalik xulosa tuzish
├── requirements.txt
├── .env.example
├── .gitignore
└── disney-bot.service     # systemd unit fayli
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

**4-bosqich (joylashtirish va debug)**
- **`disney-bot.service`:** systemd unit — VPS'да avtomatik ishga tushirish,
  nosozlikda qayta ishga tushirish.
- **Debug komandalar** (jadvalni kutmasdan qo'lda test qilish uchun):
  - `/debug` — debug komandalar ro'yxati
  - `/test_ertalabki <id>` — guruhga ertalabki xabarni yuborish
  - `/test_sorov <id>` — guruhga hisobot so'rovini yuborish
  - `/test_eslatma` — hozir hisobot bermaganlarga eslatma
  - `/test_haftalik` — haftalik tahlilni adminга yuborish
  - `/test_xulosa` — kunlik xulosani ko'rsatish

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

### Tez tekshiruv (tarmoqsiz)

Kodni haqiqiy token yoki API kalitisiz, Telegram'ga ulanmasdan sinash uchun:

```bash
python smoke_test.py
```

Bu skript soxta token bilan botning butun ulanish zanjirini (sozlamalar,
baza, routerlar, scheduler + vaqt mintaqasi, xulosalar) tekshiradi va
`SMOKE OK ...` chop etsa — hammasi joyida.

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

## VPS'га o'rnatish — eng oson yo'l (bitta buyruq)

Ubuntu/Debian VPS'да, root sifatida:

```bash
git clone -b claude/disney-report-bot-04gmgw <repo-url> disney-report-bot
cd disney-report-bot
sudo bash install.sh
```

`install.sh` hamma narsани avtomatik qiladi: paketlar, foydalanuvchi, venv,
bog'liqliklar, systemd xizmati. Faqat `BOT_TOKEN` va `ANTHROPIC_API_KEY` ни
so'raydi (`ADMIN_ID` standart `5284718368`).

Tugagach:
```bash
systemctl status disney-bot        # holat
journalctl -u disney-bot -f        # jonli log
```

---

## VPS'га o'rnatish — qo'lда (batafsil)

Agar avtomatik skript o'rniga qadamlарни qo'lда bajarmoqchi bo'lsangiz.
Bot 24/7 ishlaydi va nosozlikда avtomatik qayta ishga tushadi.

**1. Tizim tayyorligi va foydalanuvchi**

```bash
sudo apt update && sudo apt install -y python3 python3-venv git
# Bot uchun alohida (root bo'lmagan) foydalanuvchi
sudo useradd -r -m -d /opt/disney-report-bot disney
```

**2. Kodni joylashtirish**

```bash
sudo -u disney git clone <repo-url> /opt/disney-report-bot
cd /opt/disney-report-bot
sudo -u disney python3 -m venv .venv
sudo -u disney .venv/bin/pip install -r requirements.txt
```

**3. Sozlamalar (`.env`)**

```bash
sudo -u disney cp .env.example .env
sudo -u disney nano .env   # BOT_TOKEN, ADMIN_ID, ANTHROPIC_API_KEY ni to'ldiring
```

**4. systemd xizmatini o'rnatish**

```bash
sudo cp disney-bot.service /etc/systemd/system/disney-bot.service
# Unit faylдаги User/WorkingDirectory/yo'llarni tekshiring (standart: disney, /opt/disney-report-bot)
sudo systemctl daemon-reload
sudo systemctl enable --now disney-bot
```

**5. Boshqarish va loglar**

```bash
sudo systemctl status disney-bot        # holat
sudo systemctl restart disney-bot       # qayta ishga tushirish
sudo journalctl -u disney-bot -f        # jonli log
tail -f /opt/disney-report-bot/logs/bot.log
```

**Yangilash:**

```bash
cd /opt/disney-report-bot
sudo -u disney git pull
sudo -u disney .venv/bin/pip install -r requirements.txt
sudo systemctl restart disney-bot
```

## Ishga tushgach — birinchi qadamlar

1. Botni ishchi guruhlarga **admin** sifatida qo'shing → guruhlar avtomatik
   ro'yxatga olinadi va sizga xabar keladi.
2. `/vazifa` bilan har guruhga bugungi vazifalarni qo'shing.
3. Kerak bo'lsa `/vaqt` bilan so'rov/ertalab vaqtlarini moslang.
4. `/debug` komandalari orqali jadvalni kutmasdan sinab ko'ring.

## Eslatma

- Sirlar (`.env`) va baza (`data/`) `.gitignore`да — repozitoriyaga tushmaydi.
- `ANTHROPIC_API_KEY` bo'sh bo'lsa AI tekshiruv o'chadi, qolgan hamma narsa
  ishlaydi (hisobotlar `pending` holatida saqlanadi).
