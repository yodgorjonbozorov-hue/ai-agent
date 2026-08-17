"""
groups.py — guruhlardagi hodisalarni qayta ishlash.

Uch vazifa:
  1. Bot guruhga qo'shilganda (my_chat_member) — guruhni avtomatik
     ro'yxatga olish va adminга xabar berish.
  2. Guruhdan kelgan matnli xabarni hisobot sifatida qabul qilish:
     - faqat ro'yxatdagi guruhlardan;
     - so'rov (18:00) yuborilgandan keyin kelgan;
     - 50 belgidan uzun matn.
     Hisobotga javobni AI o'zi yozadi — odam nima yozgan bo'lsa, shunga
     qarab. Shablon faqat AI ishlamaganda ishlatiladi.
  3. Botga murojaat qilingan (reply yoki @username) qisqa xabarlarga
     AI javob beradi: guruh holati, vazifalar va hisobot haqida.

Qolgan oddiy suhbat xabarlariga bot aralashmaydi.
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
from services.ai import AiAssistant
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


async def _addressed_to_bot(message: Message, bot: Bot) -> bool:
    """Xabar botga murojaat qilib yozilganmi (reply yoki @username)."""
    try:
        me = await bot.me()  # aiogram natijani keshlaydi
    except Exception:
        return False

    reply = message.reply_to_message
    if reply and reply.from_user and reply.from_user.id == me.id:
        return True

    if me.username:
        return f"@{me.username}".lower() in (message.text or "").lower()
    return False


async def _group_context(group: dict, settings: Settings) -> str:
    """Botga savol berilganda AI foydalanadigan faktlar."""
    group_id = int(group["id"])
    date = reporter.today_str(settings.tz)

    tasks = await db.get_tasks(group_id, date)
    tasks_text = (
        "; ".join(t["text"] for t in tasks) if tasks else "belgilanmagan"
    )

    report = await db.get_latest_report(group_id, date)
    if report is None:
        report_text = "bugun hisobot hali kelmagan"
    else:
        author = report.get("user_name") or "noma'lum"
        report_text = f"bugungi hisobotni {author} yuborgan"

    return (
        f"Guruh nomi: {group.get('name') or 'nomsiz'}\n"
        f"Bugungi sana: {reporter.pretty_date(settings.tz)}\n"
        f"Bugungi vazifalar: {tasks_text}\n"
        f"Hisobot holati: {report_text}\n"
        f"Ertalabki xabar vaqti: {group.get('morning_time')}\n"
        f"Hisobot so'raladigan vaqt: {group.get('request_time')}\n"
        "Hisobot 4 qismdan iborat: bajarilgan ishlar; bajarilmagani va sababi; "
        "muammolar; ertangi reja."
    )


@router.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}), F.text)
async def on_group_message(
    message: Message,
    bot: Bot,
    settings: Settings,
    ai: AiAssistant,
) -> None:
    """Guruhdagi matnli xabarni hisobot yoki botga savol sifatida ko'rib chiqadi."""
    try:
        group = await db.get_group_by_chat_id(message.chat.id)
        # Faqat ro'yxatdagi va faol guruhlar
        if not group or not group.get("is_active"):
            return

        text = (message.text or "").strip()
        if not text:
            return

        group_id = int(group["id"])
        date = reporter.today_str(settings.tz)

        # Hisobot faqat so'rov yuborilgandan keyin va yetarli uzunlikda qabul qilinadi
        is_report = len(text) >= MIN_REPORT_LENGTH and await db.has_log(
            group_id, date, "request"
        )

        if is_report:
            await _handle_report(message, bot, settings, ai, group, date)
            return

        # Hisobot emas — botga murojaat qilingan bo'lsa, AI javob beradi
        if await _addressed_to_bot(message, bot):
            answer = await ai.answer(text, context=await _group_context(group, settings))
            if answer:
                await message.reply(answer)
            else:
                await message.reply(texts.AI_UNAVAILABLE)
    except Exception:
        logger.error("Guruh xabarini qayta ishlashda xato", exc_info=True)


async def _handle_report(
    message: Message,
    bot: Bot,
    settings: Settings,
    ai: AiAssistant,
    group: dict,
    date: str,
) -> None:
    """Hisobotni saqlaydi, AI orqali baholaydi va AI yozgan javobni yuboradi."""
    group_id = int(group["id"])
    text = (message.text or "").strip()

    user = message.from_user
    user_id = user.id if user else 0
    user_name = (user.full_name if user else "") or "Noma'lum"

    # Hisobotni avval 'pending' holatida saqlaymiz (AI ishlamasa ham yo'qolmaydi)
    report_id = await db.add_report(
        group_id=group_id,
        user_id=user_id,
        user_name=user_name,
        date=date,
        raw_text=text,
        status="pending",
        tz=settings.tz,
    )
    logger.info("Hisobot saqlandi: guruh %d, foydalanuvchi %s", group_id, user_name)

    tasks = await db.get_tasks(group_id, date)
    result = await ai.check_report(
        report_text=text,
        tasks=[t["text"] for t in tasks],
        group_name=group.get("name") or "",
        author=user_name,
    )

    if result is None:
        # AI ishlamadi — pending qoladi, zaxira tasdiq beramiz
        await message.reply(texts.REPORT_RECEIVED_PLAIN)
        return

    # AI natijasiga qarab hisobotni yangilaymiz
    status = "accepted" if result["toliq"] else "incomplete"
    await db.update_report_ai(
        report_id=report_id,
        status=status,
        ai_score=result["baho"],
        ai_summary=result["qisqa_xulosa"],
        missing_parts=result["yetishmagan"],
        has_problem=result["muammo_bormi"],
        problem_text=result["muammo_qisqacha"],
    )

    # Guruhga javob — matnni AI yozgan. Bo'sh bo'lsagina shablonga qaytamiz.
    reply = result["javob"]
    if not reply:
        reply = (
            texts.REPORT_ACCEPTED
            if result["toliq"]
            else texts.report_incomplete(result["yetishmagan"])
        )
    await message.reply(reply)

    # Muammo bo'lsa — adminга darhol alohida xabar
    if result["muammo_bormi"]:
        try:
            await bot.send_message(
                settings.admin_id,
                texts.admin_problem_alert(
                    group.get("name") or f"Guruh {group_id}",
                    result["muammo_qisqacha"] or "muammo qayd etildi",
                ),
            )
        except Exception:
            logger.error("Adminга muammo xabarini yuborishda xato", exc_info=True)
