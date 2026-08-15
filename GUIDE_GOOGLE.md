# Google Cloud'da tekin 24/7 server — bosqichma-bosqich

Bu yo'l bilan bot Google'ning **"Always Free" (abadiy tekin)** kichik serverida
ishlaydi: kompyuteringiz o'chsa ham bot ishlayveradi. Terminal bilishingiz
shart emas — hamma buyruq brauzerdagi oynaga nusxalanadi.

Taxminiy vaqt: **20–30 daqiqa.**

> 💳 **Karta haqida.** Google ro'yxatdan o'tishda karta so'raydi (faqat shaxsni
> tasdiqlash uchun; $300 tekin sinov krediti ham beriladi). Quyida
> ko'rsatilgan **e2-micro** serverni **us-central1** mintaqasida tanlasangiz,
> u "Always Free" limitiga kiradi va oylik hisob **$0** bo'lib turadi —
> sinov krediti tugagandan keyin ham.

---

## 0-qadam. Kalitlarni tayyorlab qo'ying

Serverda ikkita qiymat so'raladi. Ularni oldindan tayyorlab qo'ying:

| Qiymat | Qayerdan olinadi | Majburiymi |
|---|---|---|
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) → `/mybots` → botingiz → **API Token** | ✅ ha |
| `ANTHROPIC_API_KEY` | console.anthropic.com → **API Keys** → **Create Key** | ❌ yo'q |

> 🔐 **Bu kalitlarni hech kimga yubormang va hech qayerga yozib qo'ymang** —
> na chatga, na hujjatga. Ular faqat serverning o'zida, `.env` faylida
> saqlanadi. Agar kalit tasodifan boshqa joyga tushib qolsa, uni darhol
> bekor qilib (revoke / delete), yangisini yarating.

`ANTHROPIC_API_KEY` bo'lmasa ham bot to'liq ishlaydi: hisobot so'raydi,
yig'adi, eslatma yuboradi, kunlik xulosa beradi. Faqat "hisobot to'liqmi,
muammo bormi" degan avtomatik AI tahlili bo'lmaydi. Kalitni keyin ham
qo'shsa bo'ladi (pastdagi *Keyin AI ni yoqish* bo'limiga qarang).

---

## 1-qadam. Google Cloud'ga kirish

1. https://console.cloud.google.com ga o'ting, Google hisobingiz bilan kiring.
2. Agar so'rasa, **Start free / Activate** ni bosib, kartani kiriting.

## 2-qadam. Tekin serverni yaratish

Ikkita yo'l bor. **A yo'li tavsiya etiladi** — u bitta buyruq va noto'g'ri
o'lcham tanlab qo'yish xavfi yo'q.

### A yo'li — bitta buyruq (tavsiya etiladi)

1. Yuqori o'ng burchakdagi **Cloud Shell** belgisini (`>_`) bosing.
   Brauzerda terminal ochiladi — u allaqachon sizning hisobingizga ulangan,
   hech narsa o'rnatish shart emas.
2. Quyidagini **butunligicha** nusxalab, Enter bosing:

```bash
gcloud services enable compute.googleapis.com

gcloud compute instances create disney-bot \
  --zone=us-central1-a \
  --machine-type=e2-micro \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-standard
```

Birinchi buyruq 1-2 daqiqa, ikkinchisi ~30 soniya ishlaydi. Tugagach server
tayyor — va o'lchamlar aynan "Always Free" limitiga mos, ya'ni **pul
yechilmaydi**.

3. Serverga kirish (xuddi shu Cloud Shell oynasida):

```bash
gcloud compute ssh disney-bot --zone=us-central1-a
```

Birinchi marta SSH kalit yaratishni so'raydi — **Enter** bosib o'ting
(parol so'rasa, bo'sh qoldirib yana Enter). So'ng to'g'ridan-to'g'ri
**4-qadam** ga o'ting.

### B yo'li — konsolda bosish orqali

1. Yuqoridagi qidiruvga **Compute Engine** deb yozing va oching.
   (Birinchi marta **Enable** tugmasini bosishga to'g'ri keladi — 1-2 daqiqa kutadi.)
2. **Create instance** ni bosing va **aynan** quyidagilarni tanlang:

   | Sozlama | Qiymat | Nega muhim |
   |---|---|---|
   | **Name** | `disney-bot` | ixtiyoriy |
   | **Region** | `us-central1 (Iowa)` | ← tekin bo'lishi uchun **shart** |
   | **Machine type** | **E2** → `e2-micro` | ← tekin bo'lishi uchun **shart** |
   | **Boot disk** | **Change** → **Debian 12**, **Standard**, **30 GB** | 30 dan oshirmang |

3. Pastdagi **Create** ni bosing. Server ~1 daqiqada tayyor bo'ladi.

> ⚠️ **Region va machine type** ni aynan yuqoridagidek tanlang. Boshqa
> qiymatlar tekin limitga kirmaydi va oyiga pul yechiladi.

> Tarmoq (firewall) sozlamalariga tegish **shart emas**. Bot faqat o'zi
> Telegram'ga ulanadi, tashqaridan hech kim serverga kirmaydi.

## 3-qadam. Serverga kirish

Server ro'yxatida `disney-bot` qatoridagi **SSH** tugmasini bosing.
Brauzerda qora terminal oynasi ochiladi — barcha buyruqni shu yerga yozamiz.

## 4-qadam. Botni o'rnatish (2 ta buyruq)

Ochilgan oynaga quyidagini nusxalab, Enter bosing:

```bash
sudo apt-get update -y && sudo apt-get install -y git
git clone -b claude/ishni-davom-tugataylik-fu7sud https://github.com/yodgorjonbozorov-hue/ai-agent.git && cd ai-agent
```

So'ng o'rnatuvchini ishga tushiring:

```bash
sudo bash install.sh
```

Skript sizdan uchta narsani so'raydi:

- **BOT_TOKEN** — 0-qadamdagi token. (Nusxalab qo'yganda ekranda ko'rinmasligi
  mumkin — bu normal, shunchaki Enter bosing.)
- **ANTHROPIC_API_KEY** — Claude kaliti. Bo'lmasa **bo'sh qoldirib Enter** bosing.
- **ADMIN_ID** — sizning Telegram ID'ingiz. Standart qiymat `5284718368`.
  **To'g'ri bo'lsa shunchaki Enter bosing.** Bilmasangiz, Telegramda
  [@userinfobot](https://t.me/userinfobot) ga yozing — ID'ingizni aytadi.
  Noto'g'ri bo'lsa, admin xabarlari boshqa odamga ketadi.

Skript paketlarni o'rnatadi, xizmat yaratadi va botni yoqadi (~3 daqiqa).

## 5-qadam. Ishlayotganini tekshirish

```bash
systemctl status disney-bot
```

Yashil **active (running)** ko'rsangiz — bot jonli. Jonli logni ko'rish uchun:

```bash
journalctl -u disney-bot -f
```

`Polling boshlandi.` yozuvi chiqsa, bot Telegram bilan bog'landi.
(Chiqish uchun `Ctrl + C` — bu botni to'xtatmaydi.)

---

## 6-qadam. ⚠️ Privacy Mode ni o'chirish — buni o'tkazib yubormang

Telegram botlari standart holatda guruhdagi **oddiy xabarlarni ko'rmaydi** —
faqat komandalarni. Bu sozlama yoqiq qolsa, bot hisobot so'raydi, xodim
yozadi, lekin bot uni **eshitmaydi** va kechqurun sizga "hisobot yo'q" deb
xulosa yuboradi.

1. Telegramda [@BotFather](https://t.me/BotFather) ga kiring
2. `/mybots` → botingizni tanlang
3. **Bot Settings** → **Group Privacy** → **Turn off**
4. BotFather "Privacy mode is disabled" deb tasdiqlashi kerak

> Bot allaqachon guruhda bo'lsa, sozlamani o'zgartirgandan keyin uni
> guruhdan **chiqarib, qayta qo'shing** — aks holda eski sozlama kuchda qoladi.

## 7-qadam. Telegramda sinab ko'rish

1. Bot bilan **shaxsiy chatda** `/start` yozing → komandalar ro'yxati chiqadi.
2. Botni ishchi guruhga **admin** qilib qo'shing → guruh avtomatik ro'yxatga
   olinadi va sizga xabar keladi.
3. `/guruhlar` → guruh ro'yxatda turibdimi va uning **id** raqamini ko'ring.
4. Jadvalni kutmasdan darhol sinang:

   ```
   /test_sorov 1          ← guruhga hisobot so'rovini yuboradi (1 — guruh id si)
   ```

5. **Guruhda** 50 belgidan uzun hisobot yozing. Bot javob berishi kerak.
6. `/matn 1` → bot hisobotni ko'rganini tasdiqlaydi.
7. `/test_xulosa` → kunlik xulosa qanday ko'rinishini ko'rsatadi.

5-qadamda bot javob bermasa — deyarli har doim sabab **Privacy Mode**
(6-qadam). Uni o'chirib, botni guruhdan chiqarib qayta qo'shing.

---

## Keyin AI ni yoqish (kalitni o'tkazib yuborgan bo'lsangiz)

```bash
sudo nano /opt/disney-report-bot/.env
```

`ANTHROPIC_API_KEY=` qatoriga kalitni yozing, `Ctrl+O` → Enter → `Ctrl+X`
bilan saqlang, so'ng:

```bash
sudo systemctl restart disney-bot
```

## Foydali buyruqlar

```bash
sudo systemctl restart disney-bot     # qayta ishga tushirish
sudo systemctl stop disney-bot        # to'xtatish
sudo systemctl start disney-bot       # yoqish
journalctl -u disney-bot -f           # jonli log
journalctl -u disney-bot -n 100       # oxirgi 100 qator log
```

## Kodni yangilash

```bash
cd ~/ai-agent && git pull
sudo bash install.sh                  # .env o'zgarmaydi, saqlanib qoladi
```

## Hisob $0 bo'lib turishi uchun

- Serverni **e2-micro** va **us-central1** da saqlang.
- Qo'shimcha server, disk yoki tashqi IP yaratmang.
- Boot diskni 30 GB dan oshirmang.
