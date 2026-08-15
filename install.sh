#!/usr/bin/env bash
#
# install.sh — Disney Navoiy Hisobot Botni VPS'ga bir buyruqda o'rnatadi.
#
# Ishlatish (Ubuntu/Debian VPS'da, root sifatida):
#   sudo bash install.sh
#
# Skript quyidagilarni bajaradi:
#   1. Kerakli tizim paketlarini o'rnatadi (python3, venv, git)
#   2. Bot uchun alohida 'disney' foydalanuvchisini yaratadi
#   3. Kodni /opt/disney-report-bot ga ko'chiradi
#   4. Virtual muhit yaratib, bog'liqliklarni o'rnatadi
#   5. .env fayl uchun token/kalit/admin_id ni so'raydi
#   6. systemd xizmatini o'rnatib, ishga tushiradi
#
set -euo pipefail

APP_USER="disney"
APP_DIR="/opt/disney-report-bot"
SERVICE_NAME="disney-bot"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- 0. root tekshiruvi --------------------------------------------------
if [[ "${EUID}" -ne 0 ]]; then
    echo "XATO: bu skript root huquqi bilan ishlashi kerak. 'sudo bash install.sh' deb ishga tushiring."
    exit 1
fi

echo "==> 1/6  Tizim paketlarini o'rnatish..."
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git

echo "==> 2/6  '${APP_USER}' foydalanuvchisini tekshirish..."
if ! id "${APP_USER}" &>/dev/null; then
    useradd -r -m -d "${APP_DIR}" "${APP_USER}"
    echo "    Foydalanuvchi yaratildi."
else
    echo "    Foydalanuvchi allaqachon mavjud."
fi

echo "==> 3/6  Kodni ${APP_DIR} ga joylashtirish..."
mkdir -p "${APP_DIR}"
if [[ "${SCRIPT_DIR}" != "${APP_DIR}" ]]; then
    # .git va vaqtinchalik fayllarni tashlab, qolgan hammasini ko'chiramiz
    cp -r "${SCRIPT_DIR}/." "${APP_DIR}/"
    rm -rf "${APP_DIR}/.git"
fi
mkdir -p "${APP_DIR}/data" "${APP_DIR}/logs"

echo "==> 4/6  Virtual muhit va bog'liqliklar..."
python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/pip" install --upgrade pip -q
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt" -q

echo "==> 5/6  Sozlamalar (.env)..."
ENV_FILE="${APP_DIR}/.env"
if [[ -f "${ENV_FILE}" ]]; then
    echo "    .env allaqachon mavjud — o'zgartirilmadi."
else
    # Qiymatlarni muhit o'zgaruvchilaridan olamiz yoki interaktiv so'raymiz
    : "${BOT_TOKEN:=}"
    : "${ANTHROPIC_API_KEY:=}"
    : "${ADMIN_ID:=5284718368}"

    if [[ -z "${BOT_TOKEN}" ]]; then
        read -rp "    BOT_TOKEN (BotFather'dan YANGI token): " BOT_TOKEN
    fi
    if [[ -z "${ANTHROPIC_API_KEY}" ]]; then
        read -rp "    ANTHROPIC_API_KEY (bo'sh qoldirsangiz AI o'chadi): " ANTHROPIC_API_KEY
    fi
    read -rp "    ADMIN_ID [${ADMIN_ID}]: " _admin_in
    ADMIN_ID="${_admin_in:-${ADMIN_ID}}"

    cat > "${ENV_FILE}" <<EOF
BOT_TOKEN=${BOT_TOKEN}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
ADMIN_ID=${ADMIN_ID}
DB_PATH=data/bot.db
TIMEZONE=Asia/Tashkent
LOG_LEVEL=INFO
EOF
    chmod 600 "${ENV_FILE}"
    echo "    .env yaratildi."
fi

# Barcha fayllar bot foydalanuvchisiga tegishli bo'lsin
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

echo "==> 6/6  systemd xizmati..."
cp "${APP_DIR}/${SERVICE_NAME}.service" "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}"

echo ""
echo "================================================================"
echo " ✅ O'rnatish tugadi!"
echo ""
echo "  Holatni ko'rish:   systemctl status ${SERVICE_NAME}"
echo "  Jonli log:         journalctl -u ${SERVICE_NAME} -f"
echo ""
echo "  Endi botni ishchi guruhlarga ADMIN sifatida qo'shing,"
echo "  so'ng shaxsiy chatda /start yuboring."
echo "================================================================"
