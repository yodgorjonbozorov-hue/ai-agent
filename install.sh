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

    # Terminal bo'lsagina so'raymiz. Skript avtomatik ishga tushirilganda
    # (masalan Google Cloud startup-script orqali) stdin terminal emas —
    # bunda `read` xato qaytaradi va `set -e` tufayli skript o'rtada uzilib
    # qolardi. Shuning uchun `|| true` va terminal tekshiruvi kerak.
    if [[ -t 0 ]]; then
        if [[ -z "${BOT_TOKEN}" ]]; then
            read -rp "    BOT_TOKEN (BotFather'dan olingan token): " BOT_TOKEN || true
        fi
        if [[ -z "${ANTHROPIC_API_KEY}" ]]; then
            read -rp "    ANTHROPIC_API_KEY (bo'sh qoldirsangiz AI o'chadi): " ANTHROPIC_API_KEY || true
        fi
        read -rp "    ADMIN_ID [${ADMIN_ID}]: " _admin_in || true
        ADMIN_ID="${_admin_in:-${ADMIN_ID}}"
    else
        echo "    (avtomatik rejim — qiymatlar muhit o'zgaruvchilaridan olindi)"
    fi

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
systemctl enable "${SERVICE_NAME}"

# BOT_TOKEN bo'lmasa botni yoqmaymiz. Aks holda u har 5 soniyada qayta ishga
# tushib, logni xato bilan to'ldiradi (Restart=always).
if grep -q '^BOT_TOKEN=.\+$' "${ENV_FILE}"; then
    systemctl restart "${SERVICE_NAME}"
    TOKEN_BOR=1
else
    TOKEN_BOR=0
fi

echo ""
echo "================================================================"
echo " ✅ O'rnatish tugadi!"
echo ""
echo "  Holatni ko'rish:   systemctl status ${SERVICE_NAME}"
echo "  Jonli log:         journalctl -u ${SERVICE_NAME} -f"
echo ""
if [[ "${TOKEN_BOR}" -eq 1 ]]; then
    echo "  Bot yoqildi. Endi @BotFather da Privacy Mode ni o'chiring"
    echo "  (Bot Settings -> Group Privacy -> Turn off), so'ng botni ishchi"
    echo "  guruhlarga ADMIN sifatida qo'shing va shaxsiy chatda /start yozing."
else
    echo "  DIQQAT: BOT_TOKEN kiritilmadi, shuning uchun bot hali yoqilmadi."
    echo ""
    echo "  Tokenni qo'shish uchun:"
    echo "    sudo nano ${ENV_FILE}"
    echo "    (BOT_TOKEN= qatoriga tokenni yozing, Ctrl+O, Enter, Ctrl+X)"
    echo "    sudo systemctl start ${SERVICE_NAME}"
fi
echo "================================================================"
