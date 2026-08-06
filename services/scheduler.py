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

    def __init__(self, bot: Bot, settings: Settings) -> None:
        self.bot = bot
        self.settings = settings
        self.scheduler = AsyncIOScheduler(timezone=settings.tz)

    # ------------------------------------------------------------------
    # Ishga tushirish
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Barcha guruhlar uchun joblarni tuzadi va schedulerni ishga tushiradi."""
        await self.schedule_all_groups()

        # Kunlik xulosa — barcha guruhlar uchun umumiy, 22:00 da adminga
        self.scheduler.add_job(
            self._send_daily_summary,
            CronTrigger(hour=22, minute=0, timezone=self.settings.tz),
            id="daily_summary",
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

            if tasks:
                text = texts.morning_with_tasks([t["text"] for t in tasks])
            else:
                text = texts.MORNING_NO_TASKS

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
            await self.bot.send_message(group["chat_id"], texts.REPORT_REQUEST)
            await db.add_log(group_id, date, "request", self.settings.tz)
            logger.info("Hisobot so'rovi yuborildi: guruh %d", group_id)
        except Exception:
            logger.error("Hisobot so'rovi xatosi (guruh %d)", group_id, exc_info=True)

    async def _send_daily_summary(self) -> None:
        """22:00 — kunlik xulosani adminga yuboradi."""
        try:
            text = await reporter.build_daily_summary(self.settings.tz)
            await self.bot.send_message(self.settings.admin_id, text)
            date = reporter.today_str(self.settings.tz)
            await db.add_log(None, date, "daily_summary", self.settings.tz)
            logger.info("Kunlik xulosa adminga yuborildi")
        except Exception:
            logger.error("Kunlik xulosa xatosi", exc_info=True)
