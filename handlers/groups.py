"""
groups.py — guruhlardagi hodisalarni qayta ishlash.

Ikki vazifa:
  1. Bot guruhga qo'shilganda (my_chat_member) — guruhni avtomatik
     ro'yxatga olish va adminга xabar berish.
  2. Guruhdan kelgan matnli xabarni hisobot sifatida qabul qilish:
     - faqat ro'yxatdagi guruhlardan;
     - so'rov (18:00) yuborilgandan keyin kelgan;
     - 50 belgidan uzun matn.
     Qisqa "ok", "rahmat" kabi xabarlar e'tiborsiz qoldiriladi.

1-bosqichda hisobot bazaga 'pending' holatida yoziladi va oddiy tasdiq
javobi beriladi. AI tekshiruv 2-bosqichда qo'shiladi.
"""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.types import ChatMemberUpdated, Message

import database as db
import texts
from config import Settings
from services import reporter
from services.scheduler import BotScheduler

logger = logging.getLogger(__name__)

router = Router(name="groups")

# Hisobot deb qabul qilinishi uchun minimal matn uzunligi
MIN_REPORT_LENGTH = 50

# Bot faol a'zo hisoblanadigan holatlar
_ACTIVE_STATUSES = {"member", "administrator", "creator"}


@router.my_chat_member()
async def on_bot_added(
    event: ChatMemberUpdated,
    bot: Bot,
    settings: Settings,
    scheduler: BotScheduler,
) -> None:
    """Bot guruhga qo'shilganda ishga tushadi — guruhni ro'yxatga oladi."""
    chat = event.chat
    if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    new_status = event.new_chat_member.status
    old_status = event.old_chat_member.status

    # Yangi holat faol, eski holat faol emas → bot endigina qo'shildi
    if new_status in _ACTIVE_STATUSES and old_status not in _ACTIVE_STATUSES:
        try:
            group_id = await db.add_or_update_group(
                chat_id=chat.id,
                name=chat.title or "Nomsiz guruh",
                tz=settings.tz,
            )
            # Yangi guruh uchun joblarni darhol rejalashtiramiz
            group = await db.get_group_by_id(group_id)
            if group:
                scheduler.schedule_group(group)

            await bot.send_message(
                settings.admin_id,
                texts.admin_new_group(chat.title or "Nomsiz guruh", chat.id),
            )
            logger.info("Yangi guruh ro'yxatga olindi: %s (%s)", chat.title, chat.id)
        except Exception:
            logger.error("Guruhni ro'yxatga olishда xato (%s)", chat.id, exc_info=True)


@router.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}), F.text)
async def on_group_message(
    message: Message,
    settings: Settings,
) -> None:
    """Guruhdagi matnli xabarni hisobot sifatida ko'rib chiqadi."""
    try:
        group = await db.get_group_by_chat_id(message.chat.id)
        # Faqat ro'yxatdagi va faol guruhlar
        if not group or not group.get("is_active"):
            return

        text = (message.text or "").strip()

        # Qisqa xabarlar (ok, rahmat, ...) e'tiborsiz
        if len(text) < MIN_REPORT_LENGTH:
            return

        group_id = int(group["id"])
        date = reporter.today_str(settings.tz)

        # Hisobot faqat so'rov yuborilgandan keyin qabul qilinadi
        request_sent = await db.has_log(group_id, date, "request")
        if not request_sent:
            logger.debug(
                "Guruh %d: uzun xabar keldi, lekin so'rov hali yuborilmagan — o'tkazib yuborildi",
                group_id,
            )
            return

        user = message.from_user
        user_id = user.id if user else 0
        user_name = (user.full_name if user else "") or "Noma'lum"

        await db.add_report(
            group_id=group_id,
            user_id=user_id,
            user_name=user_name,
            date=date,
            raw_text=text,
            status="pending",
            tz=settings.tz,
        )
        # 1-bosqich: oddiy tasdiq (AI 2-bosqichda javob mantiqini boshqaradi)
        await message.reply(texts.REPORT_RECEIVED_PLAIN)
        logger.info("Hisobot saqlandi: guruh %d, foydalanuvchi %s", group_id, user_name)
    except Exception:
        logger.error("Guruh xabarini qayta ishlashda xato", exc_info=True)
