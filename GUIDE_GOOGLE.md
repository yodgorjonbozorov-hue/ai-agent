# Google Cloud'da TEKIN 24/7 server (bosqichma-bosqich)

Bu yo'l bilan bot Google'ning **"Always Free" (abadiy tekin)** kichik serverida
ishlaydi. Kompyuteringiz o'chsa ham bot ishlayveradi. Bu serverda disk doimiy,
shuning uchun **Turso ham kerak emas** — hammasi serverning o'zida saqlanadi.

> 💳 **Karta haqida:** Google ro'yxatdan o'tishда karta so'raydi (shaxsni
> tasdiqlash uchun). Quyidagi **e2-micro** serverни **us-central1** mintaqasida
> tanlasangiz, u "Always Free" limitiga kiradi va **pul yechilmaydi**.

---

## 1-qadam. Google Cloud'ga kirish

1. https://console.cloud.google.com ga o'ting, Google hisobingiz bilan kiring.
2. Agar so'rasa, **"Start free" / "Activate"** ni bosib, kartani kiriting
   (tasdiqlash uchun; $300 tekin sinov krediti ham beriladi).

## 2-qadam. Tekin serverni yaratish

1. Yuqoridagi qidiruvга **Compute Engine** deb yozing va oching.
   (Birinchi marta "Enable" tugmasини bosishга to'g'ri kelishi mumkin — biroz kutadi.)
2. **Create instance** ni bosing va quyidagilarni tanlang:
   - **Name:** `disney-bot`
   - **Region:** `us-central1 (Iowa)` ← muhim, tekin bo'lishi uchun
   - **Machine configuration:** **E2** → **Machine type: `e2-micro`** ← muhim
   - **Boot disk:** **Change** → OS: **Debian 12**, disk turi **Standard**, hajmi **30 GB** (30 dan oshirmang)
3. Pastda **Create** ni bosing. 1 daqiqada server tayyor bo'ladi.

## 3-qadam. Serverga kirish (brauzerдан, terminal kerak emas)

Server ro'yxatida `disney-bot` yonidagi **SSH** tugmasini bosing.
Yangi qora oynali terminal ochiladi — hamma buyruqni shu yerга yozamiz.

## 4-qadam. Botni o'rnatish (2 ta buyruq)

Ochilgan SSH oynasiga quyidagini nusxalab qo'ying (Enter bosing):

```bash
sudo apt-get update -y && sudo apt-get install -y git
git clone -b claude/ishni-davom-et-ehv38i https://github.com/yodgorjonbozorov-hue/ai-agent.git && cd ai-agent
```

> Agar `git clone` **parol/username so'rasa**, repongiz maxfiy (private) demakдир.
> Eng oson yechim: GitHub'да repoні **Public** qilib qo'ying
> (Settings → General → eng past → Change visibility → Public).
> Kodda hech qanday sir yo'q, shuning uchun bu xavfsiz. So'ng buyruqни qayta bosing.

So'ng o'rnatuvchini ishga tushiring:

```bash
sudo bash install.sh
```

Skript sizdan so'raydi:
- **BOT_TOKEN** — BotFather bergan tokenни qo'ying (@ai_yodgor_bozorov_bot niki).
- **ANTHROPIC_API_KEY** — Claude kaliti; bilmasangiz **bo'sh qoldiring** (Enter). Keyin qo'shsa bo'ladi.
- **ADMIN_ID** — shunчaki **Enter** bosing (5284718368 avtomatiк turadi).

Skript hammasini o'rnatadi va botни fon xizmati sifatida yoqadi.

## 5-qadam. Ishlaganini tekshirish

Xuddi shu SSH oynasiga:

```bash
systemctl status disney-bot
```

Yashil **active (running)** ko'rsangiz — bot jonli! Jonli logни ko'rish uchun:

```bash
journalctl -u disney-bot -f
```

`Polling boshlandi.` yozuvи chiqsa, bot ishlayapti. (Chiqish uchun `Ctrl + C`.)

## 6-qadam. Telegram'da ishlatish

1. **@ai_yodgor_bozorov_bot** ni ishchi guruhга **admin** qilib qo'shing
   → guruh avtomatiк ro'yxatga olinadi va sizга xabar keladi.
2. Bot bilan shaxsiy chatда `/start` yozing → yordam va komandalar chiqadi.

---

## Foydali buyruqlar (keyinchalik kerak bo'lsa)

```bash
sudo systemctl restart disney-bot     # qayta ishga tushirish
sudo systemctl stop disney-bot        # to'xtatish
journalctl -u disney-bot -f           # jonli log
```

## Kodни yangilash (men o'zgartirsam)

```bash
cd ~/ai-agent && git pull && sudo bash install.sh
sudo systemctl restart disney-bot
```

## Muhim: pul yechilmasligi uchun

- Serverни **e2-micro** va **us-central1**да saqlang.
- Boshqa katta serverlар yoki qo'shimcha disklар yaratmang.
- Shu holda oylik hisob **$0** bo'lib turadi.
