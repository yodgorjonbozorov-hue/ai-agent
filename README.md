# Disney Navoiy — Hisobot Bot

Ishchi guruhlardan kunlik ish hisobotlarini avtomatik so'raydigan, yig'adigan
va adminga xulosa beradigan Telegram bot.

> **Holat:** Tugallangan (1–5 bosqich). 59 ta avtomatik test o'tadi,
> systemd bilan VPS'da ishga tushirishga tayyor.

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
├── tests/                 # pytest testlari (59 ta)
│   ├── conftest.py        # vaqtinchalik baza fixture'lari
│   ├── test_database.py   # CRUD va loglar
│   ├── test_reporter.py   # kunlik xulosa, eslatma, haftalik tahlil
│   ├── test_ai_checker.py # AI javobini o'qish va normallashtirish
│   ├── test_handlers.py   # handlerlar (soxta Update bilan)
│   └── test_texts_and_scheduler.py
├── .github/workflows/
│   └── tests.yml          # CI: har push/PR da testlar
├── requirements.txt
├── requirements-dev.txt   # testlar uchun qo'shimcha paketlar
├── pytest.ini
├── .env.example
├── .gitignore
├── install.sh             # VPS uchun bir buyruqli o'rnatuvchi
└── disney-bot.service     # systemd unit fayli
```

## Hozircha nima ishlaydi

**1-bosqich**
- **Ro'yxatga olish:** bot guruhga qo'shilganda avtomatik bazaga yoziladi va
  admin xabardor qilinadi (`my_chat_member`).
- **09:00 — ertalabki xabar:** bugungi vazifalar guruhga yuboriladi
  (vazifa yo'q bo'lsa umumiy eslatma).
- **18:00 — hisobot so'rovi:** guruhga standart shablon yuboriladi.
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
- **Muammo signali:** `muammo_bormi: true` bo'lsa adminga darhol alohida xabar.
- **Xulosa boyitildi:** 22:00 xulosaga AI qisqa xulosasi va e'tibor talab
  qiladigan bandlar qo'shildi.
- **Barqarorlik:** AI kritik yo'l EMAS — timeout, rate limit yoki JSON parse
  xatosida hisobot `pending` holatida saqlanadi va bot ishlashda davom etadi.

**3-bosqich (eslatma, admin komandalari, haftalik tahlil)**
- **18:30 — 1-eslatma:** faqat hali hisobot yubormagan guruhlarga, muloyim.
- **20:00 — 2-eslatma + eskalatsiya:** guruhlarga takroriy eslatma, adminga
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
- **`disney-bot.service`:** systemd unit — VPS'da avtomatik ishga tushirish,
  nosozlikda qayta ishga tushirish.
- **Debug komandalar** (jadvalni kutmasdan qo'lda test qilish uchun):
  - `/debug` — debug komandalar ro'yxati
  - `/test_ertalabki <id>` — guruhga ertalabki xabarni yuborish
  - `/test_sorov <id>` — guruhga hisobot so'rovini yuborish
  - `/test_eslatma` — hozir hisobot bermaganlarga eslatma
  - `/test_haftalik` — haftalik tahlilni adminga yuborish
  - `/test_xulosa` — kunlik xulosani ko'rsatish

**5-bosqich (sifat, testlar va tuzatishlar)**
- **Test to'plami:** 59 ta pytest testi — baza CRUD, kunlik/haftalik xulosa,
  eslatma mantig'i, AI javobini o'qish va handlerlar (soxta Update orqali,
  Telegram API ga chiqmasdan).
- **Tuzatildi — guruhda ortiqcha javob:** admin router endi faqat shaxsiy
  chatda ishlaydi. Ilgari guruhda yozilgan `/start` ga bot "faqat admin uchun"
  deb javob berib, ishchi guruhni keraksiz xabar bilan to'ldirardi.
- **Tuzatildi — noto'g'ri hisobotlar:** boshqa botlarning xabarlari va
  komandalar (`/vazifa ...`) endi hisobot sifatida bazaga tushmaydi.
- **Tuzatildi — o'tkazib yuborilgan joblar:** har bir jobga 5 daqiqalik
  `misfire_grace_time` qo'shildi. Ilgari bot aynan o'sha daqiqada qayta ishga
  tushayotgan bo'lsa, kunlik xabar butunlay yo'qolardi.
- **Tuzatildi — matn xatolari:** lotin o'zbek matniga aralashib qolgan kirill
  harflari tozalandi (55 qator, jumladan foydalanuvchiga ko'rinadigan xabar).
  Test bu xatoning qaytalanishini tekshiradi.
- **Arzonlashtirildi:** AI so'rovi `effort: low` bilan yuboriladi — bu vazifa
  oddiy tasnif, standart `high` daraja shart emas.

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
2. Admin bilan shaxsiy chatda `/start` yuboring → yordam matni.
3. `/guruhlar` — ro'yxatni ko'ring.

## Testlar

Testlar tarmoqqa chiqmaydi va haqiqiy bazaga tegmaydi — har biri o'zining
vaqtinchalik SQLite faylida ishlaydi.

```bash
pip install -r requirements-dev.txt
python -m pytest          # 59 ta test, ~5 soniya
python -m pytest -v       # har bir test nomi bilan
```

Testlar GitHub Actions'da ham avtomatik ishlaydi: har bir push va pull
request'da (`.github/workflows/tests.yml`). Sir yoki token talab qilmaydi.

## Sozlamalar (`.env`)

| O'zgaruvchi | Izoh |
|---|---|
| `BOT_TOKEN` | BotFather'dan olingan token |
| `ANTHROPIC_API_KEY` | Claude API kaliti (bo'sh bo'lsa AI o'chadi) |
| `ADMIN_ID` | Admin Telegram ID (butun son) |
| `DB_PATH` | Baza fayli, standart `data/bot.db` |
| `TIMEZONE` | Vaqt mintaqasi, standart `Asia/Tashkent` |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

## Serverga joylashtirish — qaysi yo'lni tanlash

| Vaziyat | Yo'l |
|---|---|
| Serverim yo'q, tekin va tez kerak | **[GUIDE_GOOGLE.md](GUIDE_GOOGLE.md)** — Google Cloud "Always Free", ~25 daqiqa |
| Menda Ubuntu/Debian VPS bor | Quyidagi `install.sh` yo'li |

## VPS'ga o'rnatish — eng oson yo'l (bitta buyruq)

Ubuntu/Debian VPS'da, root sifatida:

```bash
git clone -b claude/ishni-davom-tugataylik-fu7sud <repo-url> disney-report-bot
cd disney-report-bot
sudo bash install.sh
```

`install.sh` hamma narsani avtomatik qiladi: paketlar, foydalanuvchi, venv,
bog'liqliklar, systemd xizmati. Faqat `BOT_TOKEN` va `ANTHROPIC_API_KEY` ni
so'raydi (`ADMIN_ID` standart `5284718368`).

Tugagach:
```bash
systemctl status disney-bot        # holat
journalctl -u disney-bot -f        # jonli log
```

---

## VPS'ga o'rnatish — qo'lda (batafsil)

Agar avtomatik skript o'rniga qadamlarni qo'lda bajarmoqchi bo'lsangiz.
Bot 24/7 ishlaydi va nosozlikda avtomatik qayta ishga tushadi.

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
# Unit fayldagi User/WorkingDirectory/yo'llarni tekshiring (standart: disney, /opt/disney-report-bot)
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

## ⚠️ ENG MUHIM QADAM — Privacy Mode ni o'chirish

Telegram botlari standart holatda guruhdagi **hamma xabarni ko'rmaydi** — faqat
komandalar va o'ziga javob berilgan xabarlarni ko'radi. Bu sozlama yoqiq
qolsa, xodimlar yozgan hisobotlar botga umuman yetib bormaydi: bot xabar
yuboradi, lekin javoblarni "eshitmaydi" va har kuni "hisobot yo'q" deb
xulosa beradi.

Shuning uchun botni guruhga qo'shishdan **oldin**:

1. Telegramda [@BotFather](https://t.me/BotFather) ga kiring
2. `/mybots` → botingizni tanlang
3. **Bot Settings** → **Group Privacy** → **Turn off**
4. BotFather "Privacy mode is disabled" deb tasdiqlashi kerak

Agar bot allaqachon guruhda bo'lsa, sozlamani o'zgartirgandan keyin uni
guruhdan **chiqarib, qayta qo'shing** — aks holda eski sozlama kuchda qoladi.

## Ishga tushgach — birinchi qadamlar

1. Privacy Mode o'chirilganini tekshiring (yuqoriga qarang).
2. Botni ishchi guruhlarga **admin** sifatida qo'shing → guruhlar avtomatik
   ro'yxatga olinadi va sizga xabar keladi.
3. `/vazifa` bilan har guruhga bugungi vazifalarni qo'shing.
4. Kerak bo'lsa `/vaqt` bilan so'rov/ertalab vaqtlarini moslang.
5. **Darhol sinab ko'ring** (jadvalni kutmasdan):
   - `/test_sorov <guruh_id>` — guruhga hisobot so'rovini yuboradi
   - guruhda 50 belgidan uzun hisobot yozing → bot javob berishi kerak
   - `/matn <guruh_id>` — bot hisobotni ko'rganini tasdiqlaydi
   - `/test_xulosa` — kunlik xulosa qanday ko'rinishini ko'rsatadi

## Eslatma

- Sirlar (`.env`) va baza (`data/`) `.gitignore`da — repozitoriyaga tushmaydi.
- `ANTHROPIC_API_KEY` bo'sh bo'lsa AI tekshiruv o'chadi, qolgan hamma narsa
  ishlaydi (hisobotlar `pending` holatida saqlanadi).
