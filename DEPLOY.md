# Botni bulutда 24/7 ishga tushirish (Railway) — sodda yo'riqnoma

Bu yo'l bilan bot **doim yoniq bo'ladi** — kompyuteringiz o'chsa ham ishlayveradi.
Kod yozish yoki server sozlash shart emas, hammasi brauzer orqали.

> Kichik eslatma: uzluksiz 24/7 ishlash uchun Railway oyiga taxminan **$5**
> oladi (dastlab bepul sinov krediti beriladi). Bu bulut xostining haqi.

---

## 1-qadam. Turso'dan 2 ta qiymatni oling

Botning ma'lumotlari Turso'да saqlanadi (yo'qolmaydi). Turso panelidan yoki
terminaldan quyidagilarni oling:

```bash
turso db show <baza-nomi> --url        # → TURSO_DATABASE_URL (libsql://... bilan boshlanadi)
turso db tokens create <baza-nomi>      # → TURSO_AUTH_TOKEN (uzun matn)
```

Bu ikki qiymatni nusxalab, bir joyga saqlab qo'ying — 4-qadamда kerak bo'ladi.

## 2-qadam. Railway'ga kiring

1. https://railway.app saytiga o'ting.
2. **Login with GitHub** tugmasini bosib, GitHub hisobingiz bilan kiring.

## 3-qadam. Repони ulang

1. **New Project** → **Deploy from GitHub repo** ni bosing.
2. Ro'yxatdан `ai-agent` repозиториясини tanlang.
3. **Branch** sifatida `claude/ishni-davom-et-ehv38i` ni tanlang.
4. Railway `Dockerfile` ni o'zi topib, botни quradi (build).

## 4-qadam. Sozlamalarni (Variables) kiriting

Loyiha ochilgach, **Variables** bo'limiga o'ting va quyidagilarni qo'shing
(har biri alohida: nomi = qiymati):

| Nomi | Qiymati |
|---|---|
| `BOT_TOKEN` | BotFather bergan token |
| `ADMIN_ID` | `5284718368` |
| `TURSO_DATABASE_URL` | 1-qadamдаги URL |
| `TURSO_AUTH_TOKEN` | 1-qadamдаги token |
| `ANTHROPIC_API_KEY` | Claude API kaliti *(ixtiyoriy — bo'sh qoldirsangiz AI o'chadi, bot baribir ishlaydi)* |
| `TIMEZONE` | `Asia/Tashkent` *(ixtiyoriy)* |

Saqlagach, Railway botni avtomatik qayta ishga tushiradi.

## 5-qadam. Ishlaganini tekshiring

1. Railway'да **Deploy Logs** da `Polling boshlandi.` yozuvини ko'rsangiz — bot jonli.
2. Telegram'да **@ai_yodgor_bozorov_bot** ni ishchi guruhga **admin** qilib qo'shing
   → guruh avtomatik ro'yxatga olinadi va sizga xabar keladi.
3. O'zingiz bilan shaxsiy chatда `/start` yozing → yordam matni chiqadi.

---

## Muammo bo'lsa

- **Bot javob bermayapti** → Railway loglarини tekshiring; `BOT_TOKEN` to'g'ri
  kiritilganини qarang.
- **AI baho bermayapti** → `ANTHROPIC_API_KEY` to'ldirilmagan yoki noto'g'ri.
  Bu bo'lmasa ham bot qolgan hamma ishни bajaradi (hisobotlar `pending` bo'ladi).
- **Ma'lumot yo'qolyapti** → `TURSO_DATABASE_URL` / `TURSO_AUTH_TOKEN` to'g'ri
  ekanini tekshiring; bo'sh bo'lsa ma'lumot vaqtinchalik diskда saqlanadi.

## VPS'ni afzal ko'rsangiz

Railway o'rniga o'z serveringiz (VPS) bo'lsa, `README.md` dagi
`sudo bash install.sh` bitta buyruq bilan hammasini o'rnatadi.
