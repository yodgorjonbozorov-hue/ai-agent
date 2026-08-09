# Disney Navoiy Hisobot Bot — konteyner obrazi.
# Bot long-polling ishlaydi (web port kerak emas). Sozlamalar host
# tomonidan muhit o'zgaruvchilari orqali beriladi (BOT_TOKEN, ADMIN_ID,
# ANTHROPIC_API_KEY, TURSO_DATABASE_URL, TURSO_AUTH_TOKEN).
#
# Turso ishlatilsa lokal disk kerak emas — shuning uchun bu obraz
# diski "vaqtinchalik" bo'lgan hostlarда (Railway, Render, Koyeb, Fly.io)
# ham xavfsiz ishlaydi.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Avval bog'liqliklar (Docker qatlam keshidan foydalanish uchun)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# So'ng kod
COPY . .

# Root bo'lmagan foydalanuvchi (xavfsizlik)
RUN useradd -m appuser && chown -R appuser /app
USER appuser

CMD ["python", "bot.py"]
