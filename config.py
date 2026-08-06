"""
config.py — sozlamalarni .env fayldan o'qish.

Barcha sirlar (token, API kalit, admin ID) faqat shu yerda,
muhit o'zgaruvchilaridan olinadi. Kod ichida hech qanday sir yozilmaydi.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

# .env faylni yuklaymiz (agar mavjud bo'lsa)
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Botning barcha sozlamalari — bir joyda, o'zgarmas."""

    bot_token: str
    anthropic_api_key: str
    admin_id: int
    db_path: str
    timezone_name: str
    log_level: str

    @property
    def tz(self) -> ZoneInfo:
        """Vaqt mintaqasi obyekti (Asia/Tashkent)."""
        return ZoneInfo(self.timezone_name)


def _require(name: str) -> str:
    """Majburiy muhit o'zgaruvchisini oladi, bo'lmasa xato beradi."""
    value = os.getenv(name, "").strip()
    if not value:
        print(f"XATO: '{name}' muhit o'zgaruvchisi .env faylda ko'rsatilmagan.")
        sys.exit(1)
    return value


def load_settings() -> Settings:
    """.env dan sozlamalarni o'qib, Settings obyektini qaytaradi."""
    bot_token = _require("BOT_TOKEN")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()  # 2-bosqichda majburiy bo'ladi

    admin_id_raw = _require("ADMIN_ID")
    try:
        admin_id = int(admin_id_raw)
    except ValueError:
        print("XATO: ADMIN_ID butun son bo'lishi kerak.")
        sys.exit(1)

    db_path = os.getenv("DB_PATH", "data/bot.db").strip()
    timezone_name = os.getenv("TIMEZONE", "Asia/Tashkent").strip()
    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    # data/ jildini oldindan yaratamiz
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    return Settings(
        bot_token=bot_token,
        anthropic_api_key=anthropic_api_key,
        admin_id=admin_id,
        db_path=db_path,
        timezone_name=timezone_name,
        log_level=log_level,
    )


def setup_logging(log_level: str) -> None:
    """Loglarni ham konsolga, ham faylga yozadigan qilib sozlaydi."""
    Path("logs").mkdir(exist_ok=True)

    level = getattr(logging, log_level, logging.INFO)
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    logging.basicConfig(
        level=level,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/bot.log", encoding="utf-8"),
        ],
    )
    # aiogram va apscheduler loglarini biroz jim qilamiz
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
