"""
scheduler.py — kunlik jadval vazifalari (APScheduler).

Har bir guruh uchun alohida job yaratiladi. Vaqtlar bazadan olinadi;
vaqt o'zgartirilganda job qayta rejalashtiriladi (reschedule_group).

1-bosqich joblari:
  - ertalabki xabar (morning_time, standart 09:00)
  - hisobot so'rovi (request_time, standart 18:00)
  - kunlik xulosa adminga (22:00, AI'siz)

Keyingi bosqichlarda 18:30 va 20:00 eslatma/eskalatsiya qo'shiladi.
"""

from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import database as db
import texts
from config import Settings
from services import reporter
from services.ai import AiAssistant

logger = logging.getLogger(__name__)


def _parse_hm(value: str, default: tuple[int, int]) -> tuple[int, int]:
    """'18:00' -> (18, 0). Xato bo'lsa default qaytaradi."""
    try:
        hh, mm = value.strip().split(":")
        return int(hh), int(mm)
    except (ValueError, AttributeError):
        logger.warning("Noto'g'ri vaqt formati: %r, standart ishlatildi", value)
        return default


class BotScheduler:
    """Botning barcha rejalashtirilgan vazifalarini boshqaradi."""

    def __init__(self, bot: Bot, settings: Settings, ai: AiAssistant) -> None:
        self.bot = bot
        self.settings = settings
        self.ai = ai
        self.scheduler = AsyncIOScheduler(timezone=settings.tz)

    # ------------------------------------------------------------------
    # Ishga tushirish
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Barcha guruhlar uchun joblarni tuzadi va schedulerni ishga tushiradi."""
        await self.schedule_all_groups()

        tz = self.settings.tz

        # 18:30 — 1-eslatma (hali hisobot yubormaganlarga, muloyim)
        self.scheduler.add_job(
            self._send_reminders_soft,
            CronTrigger(hour=18, minute=30, timezone=tz),
            id="reminder_soft",
            replace_existing=True,
        )
        # 20:00 — 2-eslatma + adminга eskalatsiya
        self.scheduler.add_job(
            self._send_reminders_firm,
            CronTrigger(hour=20, minute=0, timezone=tz),
            id="reminder_firm",
            replace_existing=True,
        )
        # 22:00 — kunlik xulosa adminga
        self.scheduler.add_job(
            self._send_daily_summary,
            CronTrigger(hour=22, minute=0, timezone=tz),
            id="daily_summary",
            replace_existing=True,
        )
        # Shanba 20:00 — haftalik tahlil adminga
        self.scheduler.add_job(
            self._send_weekly,
            CronTrigger(day_of_week="sat", hour=20, minute=0, timezone=tz),
            id="weekly",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("Scheduler ishga tushdi. Jami joblar: %d",
                    len(self.scheduler.get_jobs()))

    async def schedule_all_groups(self) -> None:
        """Bazadagi barcha faol guruhlar uchun joblarni tuzadi."""
        groups = await db.get_all_groups(only_active=True)
        for g in groups:
            self.schedule_group(g)

    # ------------------------------------------------------------------
    # Guruh joblari
    # ------------------------------------------------------------------

    def schedule_group(self, group: dict[str, Any]) -> None:
        """Bitta guruh uchun ertalabki va so'rov joblarini yaratadi."""
        gid = int(group["id"])

        m_hh, m_mm = _parse_hm(group.get("morning_time", "09:00"), (9, 0))
        r_hh, r_mm = _parse_hm(group.get("request_time", "18:00"), (18, 0))

        self.scheduler.add_job(
            self._send_morning,
            CronTrigger(hour=m_hh, minute=m_mm, timezone=self.settings.tz),
            id=f"morning_{gid}",
            args=[gid],
            replace_existing=True,
        )
        self.scheduler.add_job(
            self._send_request,
            CronTrigger(hour=r_hh, minute=r_mm, timezone=self.settings.tz),
            id=f"request_{gid}",
            args=[gid],
            replace_existing=True,
        )
        logger.info(
            "Guruh %d rejalashtirildi: ertalab %02d:%02d, so'rov %02d:%02d",
            gid, m_hh, m_mm, r_hh, r_mm,
        )

    def reschedule_group(self, group: dict[str, Any]) -> None:
        """Guruh vaqtlari o'zgarganda joblarni qayta tuzadi."""
        self.schedule_group(group)  # replace_existing=True bo'lgani uchun yetarli

    def remove_group(self, group_id: int) -> None:
        """Guruh pauza qilinganda uning joblarini o'chiradi."""
        for prefix in ("morning", "request"):
            job_id = f"{prefix}_{group_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
        logger.info("Guruh %d joblari o'chirildi", group_id)

    # ------------------------------------------------------------------
    # Job funksiyalari (barchasi try/except bilan himoyalangan)
    # ------------------------------------------------------------------

    async def _send_morning(self, group_id: int) -> None:
        """09:00 — bugungi vazifalarni guruhga yuboradi."""
        try:
            group = await db.get_group_by_id(group_id)
            if not group or not group.get("is_active"):
                return

            date = reporter.today_str(self.settings.tz)
            tasks = await db.get_tasks(group_id, date)
            task_list = [t["text"] for t in tasks]

            # Matnni AI yozadi; ishlamasa shablonga qaytamiz
            if task_list:
                fallback = texts.morning_with_tasks(task_list)
                task_prompt = (
                    "Guruhga ertalabki xabar yoz: salomlash va bugungi vazifalarni "
                    "raqamlangan ro'yxat qilib ko'rsat. Oxirida kun oxirida hisobot "
                    "kutilishini eslatib qo'y. Vazifalar matnini o'zgartirma."
                )
            else:
                fallback = texts.MORNING_NO_TASKS
                task_prompt = (
                    "Guruhga qisqa ertalabki xabar yoz. Bugunga alohida vazifa "
                    "belgilanmagan, shuning uchun rejadagi ishlarni davom ettirishni "
                    "va kun oxirida hisobot kutilishini ayt. Vazifa o'ylab topma."
                )

            context = (
                f"Guruh: {group.get('name') or 'nomsiz'}\n"
                f"Sana: {reporter.pretty_date(self.settings.tz)}\n"
                "Bugungi vazifalar:\n"
                + ("\n".join(f"- {t}" for t in task_list) if task_list else "(yo'q)")
            )
            text = await self.ai.compose(task_prompt, context) or fallback

            await self.bot.send_message(group["chat_id"], text)
            await db.add_log(group_id, date, "morning", self.settings.tz)
            logger.info("Ertalabki xabar yuborildi: guruh %d", group_id)
        except Exception:
            logger.error("Ertalabki xabar xatosi (guruh %d)", group_id, exc_info=True)

    async def _send_request(self, group_id: int) -> None:
        """18:00 — hisobot so'rovini guruhga yuboradi."""
        try:
            group = await db.get_group_by_id(group_id)
            if not group or not group.get("is_active"):
                return

            date = reporter.today_str(self.settings.tz)
            tasks = await db.get_tasks(group_id, date)
            task_list = [t["text"] for t in tasks]

            text = await self.ai.compose(
                "Guruhdan kunlik hisobot so'ra. Xabar oxirida hisobot tuzilishini "
                "aynan shu 4 band bilan ko'rsat: 1) Bajarilgan ishlar 2) Bajarilmagani "
                "va sababi 3) Muammolar / kerak bo'lgan yordam 4) Ertangi reja.",
                context=(
                    f"Guruh: {group.get('name') or 'nomsiz'}\n"
                    f"Sana: {reporter.pretty_date(self.settings.tz)}\n"
                    "Bugun ertalab berilgan vazifalar:\n"
                    + ("\n".join(f"- {t}" for t in task_list) if task_list else "(yo'q)")
                ),
            ) or texts.REPORT_REQUEST

            await self.bot.send_message(group["chat_id"], text)
            await db.add_log(group_id, date, "request", self.settings.tz)
            logger.info("Hisobot so'rovi yuborildi: guruh %d", group_id)
        except Exception:
            logger.error("Hisobot so'rovi xatosi (guruh %d)", group_id, exc_info=True)

    async def _reminder_text(self, group: dict[str, Any], firm: bool) -> str:
        """Eslatma matnini AI yozadi; ishlamasa shablon qaytadi."""
        if firm:
            task = (
                "Hisobot hali kelmagan guruhga takroriy eslatma yoz. Bu ikkinchi "
                "eslatma, shuning uchun ohang aniqroq va qat'iyroq bo'lsin, lekin "
                "qo'pol emas. Kun yakunlanishidan oldin yuborish kerakligini ayt."
            )
            fallback = texts.REMINDER_FIRM
        else:
            task = (
                "Hisobot hali kelmagan guruhga muloyim, qisqa eslatma yoz. "
                "Ayblamasdan, iltimos qilib so'ra."
            )
            fallback = texts.REMINDER_SOFT

        context = (
            f"Guruh: {group.get('name') or 'nomsiz'}\n"
            f"Hisobot so'ralgan vaqt: {group.get('request_time')}"
        )
        return await self.ai.compose(task, context, max_tokens=300) or fallback

    async def _send_reminders_soft(self) -> None:
        """18:30 — hali hisobot yubormagan guruhlarga muloyim eslatma."""
        try:
            date = reporter.today_str(self.settings.tz)
            missing = await reporter.missing_groups_today(self.settings.tz)
            for g in missing:
                try:
                    text = await self._reminder_text(g, firm=False)
                    await self.bot.send_message(g["chat_id"], text)
                    await db.add_log(int(g["id"]), date, "reminder_soft", self.settings.tz)
                except Exception:
                    logger.error("1-eslatma xatosi (guruh %s)", g.get("id"), exc_info=True)
            logger.info("1-eslatma yuborildi: %d guruh", len(missing))
        except Exception:
            logger.error("1-eslatma umumiy xatosi", exc_info=True)

    async def _send_reminders_firm(self) -> None:
        """20:00 — takroriy eslatma guruhlarga + adminга eskalatsiya."""
        try:
            date = reporter.today_str(self.settings.tz)
            missing = await reporter.missing_groups_today(self.settings.tz)

            for g in missing:
                try:
                    text = await self._reminder_text(g, firm=True)
                    await self.bot.send_message(g["chat_id"], text)
                    await db.add_log(int(g["id"]), date, "reminder_firm", self.settings.tz)
                except Exception:
                    logger.error("2-eslatma xatosi (guruh %s)", g.get("id"), exc_info=True)

            # Adminга javob bermaganlar ro'yxati
            names = [g.get("name") or f"Guruh {g['id']}" for g in missing]
            if names:
                await self.bot.send_message(
                    self.settings.admin_id, texts.admin_escalation(names)
                )
            await db.add_log(None, date, "escalation", self.settings.tz)
            logger.info("2-eslatma + eskalatsiya: %d guruh", len(missing))
        except Exception:
            logger.error("2-eslatma/eskalatsiya xatosi", exc_info=True)

    async def _send_daily_summary(self) -> None:
        """22:00 — kunlik xulosani adminga yuboradi."""
        try:
            text = await reporter.build_daily_summary(self.settings.tz, self.ai)
            await self.bot.send_message(self.settings.admin_id, text)
            date = reporter.today_str(self.settings.tz)
            await db.add_log(None, date, "daily_summary", self.settings.tz)
            logger.info("Kunlik xulosa adminga yuborildi")
        except Exception:
            logger.error("Kunlik xulosa xatosi", exc_info=True)

    async def _send_weekly(self) -> None:
        """Shanba 20:00 — haftalik tahlilni adminga yuboradi."""
        try:
            text = await reporter.build_weekly_analysis(self.settings.tz, self.ai)
            await self.bot.send_message(self.settings.admin_id, text)
            date = reporter.today_str(self.settings.tz)
            await db.add_log(None, date, "weekly", self.settings.tz)
            logger.info("Haftalik tahlil adminga yuborildi")
        except Exception:
            logger.error("Haftalik tahlil xatosi", exc_info=True)

    # ------------------------------------------------------------------
    # Debug uchun qo'lda ishga tushirish (admin komandalari chaqiradi)
    # ------------------------------------------------------------------

    async def trigger_morning(self, group_id: int) -> None:
        """Ertalabki xabarni qo'lda yuboradi."""
        await self._send_morning(group_id)

    async def trigger_request(self, group_id: int) -> None:
        """Hisobot so'rovini qo'lda yuboradi."""
        await self._send_request(group_id)

    async def trigger_reminders(self) -> None:
        """Eslatmalarni qo'lda yuboradi (muloyim)."""
        await self._send_reminders_soft()

    async def trigger_weekly(self) -> None:
        """Haftalik tahlilni qo'lda yuboradi."""
        await self._send_weekly()
