"""
smoke_test.py — tarmoqsiz ishga tushirish sinovi.

Botning butun ulanish zanjirini SOXTA token bilan tekshiradi va AI'ni
o'chirib qo'yadi (bo'sh ANTHROPIC_API_KEY). Telegram'ga yoki Anthropic'ga
hech qanday tarmoq so'rovi yubormaydi — `start_polling` chaqirilmaydi.

Nimalarni tekshiradi:
  - sozlamalar (.env o'rniga muhit o'zgaruvchilari) va log sozlash;
  - baza sxemasi va CRUD (guruh, hisobot, log);
  - aiogram routerlari ulanishi;
  - APScheduler + zoneinfo.ZoneInfo integratsiyasi (asosiy + guruh joblari);
  - vaqt o'zgarganda qayta rejalashtirish, pauza qilinganda job o'chirish;
  - kunlik/haftalik xulosa tuzilishi;
  - AI o'chirilgan holatda hisobot 'pending' yo'li.

Ishga tushirish (repozitoriya ildizidan):
    python smoke_test.py

Muvaffaqiyatli tugasa "SMOKE OK ..." chop etadi va 0 kod bilan chiqadi.
"""

from __future__ import annotations

import asyncio
import os
import tempfile


def _prepare_env() -> None:
    """Soxta, xavfsiz sozlamalar — hech qanday haqiqiy sir ishlatilmaydi."""
    tmp = tempfile.mkdtemp(prefix="disney-smoke-")
    os.environ["BOT_TOKEN"] = "123456789:AAImDUMMYtokenForSmokeTestOnly_0123456789x"
    os.environ["ADMIN_ID"] = "5284718368"
    os.environ["ANTHROPIC_API_KEY"] = ""  # bo'sh → AI tekshiruv o'chadi
    os.environ["DB_PATH"] = os.path.join(tmp, "smoke.db")
    os.environ["LOG_LEVEL"] = "WARNING"


async def _run() -> None:
    from aiogram import Bot, Dispatcher
    from aiogram.fsm.storage.memory import MemoryStorage

    import database as db
    from config import load_settings, setup_logging
    from handlers import admin, groups
    from services import reporter
    from services.ai_checker import AiChecker
    from services.scheduler import BotScheduler

    settings = load_settings()
    setup_logging(settings.log_level)

    await db.init_db(settings.db_path)

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    scheduler = BotScheduler(bot=bot, settings=settings)
    ai_checker = AiChecker(api_key=settings.anthropic_api_key)
    assert ai_checker.enabled is False, "bo'sh kalit AI'ni o'chirishi kerak"

    dp["settings"] = settings
    dp["scheduler"] = scheduler
    dp["ai_checker"] = ai_checker
    dp.include_router(admin.router)
    dp.include_router(groups.router)

    # APScheduler'ni zoneinfo.ZoneInfo bilan ishga tushiramiz (asosiy joblar).
    await scheduler.start()
    base_jobs = len(scheduler.scheduler.get_jobs())
    assert base_jobs >= 4, f"kamida 4 ta asosiy job kutildi, {base_jobs} topildi"

    # Guruhni ro'yxatga olish va uning joblarini tekshirish.
    gid = await db.add_or_update_group(chat_id=-100123, name="Test Guruh", tz=settings.tz)
    scheduler.schedule_group(await db.get_group_by_id(gid))
    assert scheduler.scheduler.get_job(f"morning_{gid}") is not None
    assert scheduler.scheduler.get_job(f"request_{gid}") is not None

    # Vaqtni o'zgartirish → qayta rejalashtirish; pauza → job o'chishi.
    await db.update_group_time(gid, "request_time", "17:30")
    scheduler.reschedule_group(await db.get_group_by_id(gid))
    scheduler.remove_group(gid)
    assert scheduler.scheduler.get_job(f"request_{gid}") is None

    # Hisobot + AI natijasini saqlash + xulosalar tuzilishi.
    await db.set_group_active(gid, True)
    date = reporter.today_str(settings.tz)
    await db.add_log(gid, date, "request", settings.tz)
    rid = await db.add_report(gid, 5284718368, "Tester", date, "x" * 60, "pending", settings.tz)
    await db.update_report_ai(rid, "accepted", 4, "Yaxshi hisobot",
                              ["ertangi reja"], True, "muammo qayd etildi")
    daily = await reporter.build_daily_summary(settings.tz)
    weekly = await reporter.build_weekly_analysis(settings.tz)
    missing = await reporter.missing_groups_today(settings.tz)
    assert "Test Guruh" in daily
    assert isinstance(weekly, str) and weekly
    assert missing == [], "hisobot bergan guruh 'javob bermaganlar'da bo'lmasligi kerak"

    scheduler.scheduler.shutdown(wait=False)
    await bot.session.close()

    print(f"SMOKE OK | asosiy joblar={base_jobs} | xulosalar tuzildi | AI-off yo'li ishladi")


def main() -> None:
    _prepare_env()
    asyncio.run(_run())


if __name__ == "__main__":
    main()
