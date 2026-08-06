"""
admin.py — admin komandalari (faqat shaxsiy chatda, faqat ADMIN_ID uchun).

1-bosqichda asosiy komandalar:
  /start        — yordam matni
  /guruhlar     — guruhlar ro'yxati va bugungi hisobot holati
  /hisobot      — bugungi umumiy holat (hozirgi payt uchun)
  /test_xulosa  — kunlik xulosani darhol tekshirish uchun (debug)

To'liq interaktiv komandalar (/vazifa, /vaqt, /pauza, /faol, /matn,
/haftalik) 3-bosqichда qo'shiladi.
"""

from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message

import database as db
import texts
from config import Settings
from services import reporter

logger = logging.getLogger(__name__)

router = Router(name="admin")


def _is_admin(message: Message, settings: Settings) -> bool:
    """Xabar admindan, shaxsiy chatдан kelganini tekshiradi."""
    if message.chat.type != ChatType.PRIVATE:
        return False
    return bool(message.from_user and message.from_user.id == settings.admin_id)


@router.message(Command("start"))
async def cmd_start(message: Message, settings: Settings) -> None:
    """Yordam matnini ko'rsatadi."""
    if not _is_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    await message.answer(texts.ADMIN_START)


@router.message(Command("gurular", "guruhlar"))
async def cmd_groups(message: Message, settings: Settings) -> None:
    """Barcha guruhlar ro'yxati va bugungi hisobot holati."""
    if not _is_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    try:
        groups = await db.get_all_groups()
        if not groups:
            await message.answer("Hozircha birorta guruh ro'yxatда yo'q.")
            return

        date = reporter.today_str(settings.tz)
        reports = await db.get_reports_for_date(date)

        lines = [
            texts.group_list_line(g, int(g["id"]) in reports) for g in groups
        ]
        await message.answer("📋 Guruhlar:\n\n" + "\n\n".join(lines))
    except Exception:
        logger.error("/guruhlar xatosi", exc_info=True)
        await message.answer("Xatolik yuz berdi. Loglarni tekshiring.")


@router.message(Command("hisobot"))
async def cmd_status(message: Message, settings: Settings) -> None:
    """Bugungi umumiy holatni ko'rsatadi (hozirgi payt uchun)."""
    if not _is_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    try:
        text = await reporter.build_daily_summary(settings.tz)
        await message.answer(text)
    except Exception:
        logger.error("/hisobot xatosi", exc_info=True)
        await message.answer("Xatolik yuz berdi. Loglarni tekshiring.")


@router.message(Command("test_xulosa"))
async def cmd_test_summary(message: Message, settings: Settings) -> None:
    """Debug: kunlik xulosani darhol tuzib ko'rsatadi."""
    if not _is_admin(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return

    try:
        text = await reporter.build_daily_summary(settings.tz)
        await message.answer("🧪 (test)\n\n" + text)
    except Exception:
        logger.error("/test_xulosa xatosi", exc_info=True)
        await message.answer("Xatolik yuz berdi. Loglarni tekshiring.")
