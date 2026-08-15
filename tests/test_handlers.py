"""
test_handlers.py — handler qatlamining integratsion testlari.

Bu yerda haqiqiy Dispatcher ishlatiladi va unga soxta Update yuboriladi.
Telegram API ga chiqmaslik uchun `Message.answer` / `Message.reply`
metodlari almashtiriladi — yuborilgan matnlar ro'yxatga yig'iladi.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, Update, User

import database as db
import texts
from config import Settings
from handlers import admin, groups
from services.ai_checker import AiChecker
from services.scheduler import BotScheduler

TZ = ZoneInfo("Asia/Tashkent")
ADMIN_ID = 5284718368
GROUP_CHAT_ID = -1001234567890

UZUN_MATN = (
    "1. Bajarilgan ishlar: uchta obyektda devor suvash tugadi.\n"
    "2. Bajarilmagani: elektr chizmasi kechikdi.\n"
    "3. Muammolar: yo'q.\n"
    "4. Ertangi reja: bo'yash boshlanadi."
)


@pytest.fixture
def settings(tmp_path):
    return Settings(
        bot_token="123456:TEST",
        anthropic_api_key="",  # AI o'chirilgan — tarmoqqa chiqilmaydi
        admin_id=ADMIN_ID,
        db_path=str(tmp_path / "bot.db"),
        timezone_name="Asia/Tashkent",
        log_level="ERROR",
    )


@pytest.fixture
def sent(monkeypatch):
    """Botdan chiqqan barcha matnlarni ushlab qoluvchi ro'yxat."""
    yuborilgan: list[str] = []

    async def fake_answer(self, text, **kwargs):
        yuborilgan.append(text)

    monkeypatch.setattr(Message, "answer", fake_answer, raising=False)
    monkeypatch.setattr(Message, "reply", fake_answer, raising=False)
    return yuborilgan


@pytest.fixture
async def dispatcher(settings):
    await db.init_db(settings.db_path)
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    dp["settings"] = settings
    dp["scheduler"] = BotScheduler(bot=bot, settings=settings)
    dp["ai_checker"] = AiChecker(api_key=settings.anthropic_api_key)
    dp.include_router(admin.router)
    dp.include_router(groups.router)
    yield dp, bot
    await bot.session.close()
    db.set_db_path("data/bot.db")
    # Routerlar modul darajasidagi yagona obyekt — keyingi test o'z
    # Dispatcher'iga ulay olishi uchun bog'lanishni uzamiz.
    admin.router._parent_router = None
    groups.router._parent_router = None


def _message(text: str, *, chat_id: int, chat_type: str, user_id: int,
             is_bot: bool = False) -> Update:
    return Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=datetime.now(TZ),
            chat=Chat(id=chat_id, type=chat_type),
            from_user=User(id=user_id, is_bot=is_bot, first_name="Ali"),
            text=text,
        ),
    )


def _group_message(text: str, *, user_id: int = 777, is_bot: bool = False) -> Update:
    return _message(text, chat_id=GROUP_CHAT_ID, chat_type="supergroup",
                    user_id=user_id, is_bot=is_bot)


# --------------------------------------------------------------------------
# Admin komandalari faqat shaxsiy chatda
# --------------------------------------------------------------------------

async def test_admin_shaxsiy_chatda_yordam_oladi(dispatcher, sent):
    dp, bot = dispatcher
    await dp.feed_update(bot, _message(
        "/start", chat_id=ADMIN_ID, chat_type="private", user_id=ADMIN_ID))
    assert sent == [texts.ADMIN_START]


async def test_begona_odam_admin_komandasini_ishlata_olmaydi(dispatcher, sent):
    dp, bot = dispatcher
    await dp.feed_update(bot, _message(
        "/guruhlar", chat_id=999, chat_type="private", user_id=999))
    assert sent == [texts.NOT_ADMIN]


async def test_guruhda_start_ga_javob_bermaydi(dispatcher, sent):
    """Guruhda /start yozilsa bot jim turishi kerak — guruh chati botniki emas."""
    dp, bot = dispatcher
    await dp.feed_update(bot, _group_message("/start"))
    assert sent == []


# --------------------------------------------------------------------------
# Guruhdagi hisobotlar
# --------------------------------------------------------------------------

async def test_royxatdan_otmagan_guruh_etiborsiz(dispatcher, sent):
    dp, bot = dispatcher
    await dp.feed_update(bot, _group_message(UZUN_MATN))
    assert sent == []


async def test_sorovdan_oldin_kelgan_matn_hisobot_emas(dispatcher, sent, settings):
    """18:00 so'rovi yuborilmaguncha uzun xabar oddiy suhbat deb qaraladi."""
    dp, bot = dispatcher
    gid = await db.add_or_update_group(GROUP_CHAT_ID, "Test guruh", tz=TZ)

    await dp.feed_update(bot, _group_message(UZUN_MATN))

    assert sent == []
    from services import reporter
    assert await db.get_latest_report(gid, reporter.today_str(TZ)) is None


async def test_sorovdan_keyin_hisobot_saqlanadi(dispatcher, sent):
    dp, bot = dispatcher
    gid = await db.add_or_update_group(GROUP_CHAT_ID, "Test guruh", tz=TZ)
    from services import reporter
    bugun = reporter.today_str(TZ)
    await db.add_log(gid, bugun, "request", TZ)

    await dp.feed_update(bot, _group_message(UZUN_MATN))

    # AI o'chirilgan — hisobot 'pending' holatida saqlanadi va oddiy tasdiq beriladi
    assert sent == [texts.REPORT_RECEIVED_PLAIN]
    report = await db.get_latest_report(gid, bugun)
    assert report is not None
    assert report["status"] == "pending"
    assert report["raw_text"] == UZUN_MATN
    assert report["user_name"] == "Ali"


async def test_qisqa_xabar_hisobot_emas(dispatcher, sent):
    dp, bot = dispatcher
    gid = await db.add_or_update_group(GROUP_CHAT_ID, "Test guruh", tz=TZ)
    from services import reporter
    bugun = reporter.today_str(TZ)
    await db.add_log(gid, bugun, "request", TZ)

    await dp.feed_update(bot, _group_message("rahmat, tushunarli"))

    assert sent == []
    assert await db.get_latest_report(gid, bugun) is None


async def test_komanda_hisobot_sifatida_saqlanmaydi(dispatcher, sent):
    dp, bot = dispatcher
    gid = await db.add_or_update_group(GROUP_CHAT_ID, "Test guruh", tz=TZ)
    from services import reporter
    bugun = reporter.today_str(TZ)
    await db.add_log(gid, bugun, "request", TZ)

    await dp.feed_update(bot, _group_message("/vazifa " + UZUN_MATN))

    assert sent == []
    assert await db.get_latest_report(gid, bugun) is None


async def test_boshqa_botning_xabari_hisobot_emas(dispatcher, sent):
    dp, bot = dispatcher
    gid = await db.add_or_update_group(GROUP_CHAT_ID, "Test guruh", tz=TZ)
    from services import reporter
    bugun = reporter.today_str(TZ)
    await db.add_log(gid, bugun, "request", TZ)

    await dp.feed_update(bot, _group_message(UZUN_MATN, user_id=1000, is_bot=True))

    assert sent == []
    assert await db.get_latest_report(gid, bugun) is None


async def test_pauzadagi_guruhdan_hisobot_qabul_qilinmaydi(dispatcher, sent):
    dp, bot = dispatcher
    gid = await db.add_or_update_group(GROUP_CHAT_ID, "Test guruh", tz=TZ)
    from services import reporter
    bugun = reporter.today_str(TZ)
    await db.add_log(gid, bugun, "request", TZ)
    await db.set_group_active(gid, False)

    await dp.feed_update(bot, _group_message(UZUN_MATN))

    assert sent == []
    assert await db.get_latest_report(gid, bugun) is None
