"""
bot.py — botning kirish nuqtasi.

Vazifasi:
  - sozlamalarni yuklash va logni sozlash;
  - bazani tayyorlash;
  - Bot va Dispatcher yaratish, handlerlarni ulash;
  - schedulerni ishga tushirish;
  - polling'ni boshlash.

Ishga tushirish:  python bot.py
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import database as db
from config import load_settings, setup_logging
from handlers import admin, groups
from services.ai_checker import AiChecker
from services.scheduler import BotScheduler

logger = logging.getLogger(__name__)


async def main() -> None:
    """Botning asosiy asinxron oqimi."""
    settings = load_settings()
    setup_logging(settings.log_level)

    logger.info("Disney Navoiy Hisobot Bot ishga tushmoqda...")

    # Baza
    await db.init_db(settings.db_path)

    # Bot va Dispatcher (interaktiv komandalar uchun FSM xotirasi bilan)
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Scheduler va AI tekshiruvchi
    scheduler = BotScheduler(bot=bot, settings=settings)
    ai_checker = AiChecker(api_key=settings.anthropic_api_key)

    # Handlerlarga umumiy obyektlarni uzatamiz (workflow_data orqali)
    dp["settings"] = settings
    dp["scheduler"] = scheduler
    dp["ai_checker"] = ai_checker

    # Routerlarni ulaymiz (admin — shaxsiy chat, groups — guruhlar)
    dp.include_router(admin.router)
    dp.include_router(groups.router)

    # Schedulerni ishga tushiramiz
    await scheduler.start()

    # Eski yangilanishlarni tashlab, polling'ni boshlaymiz
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Polling boshlandi.")
        await dp.start_polling(bot)
    finally:
        if scheduler.scheduler.running:
            scheduler.scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("Bot qo'lda to'xtatildi.")
