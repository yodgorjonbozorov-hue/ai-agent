"""
admin.py — admin komandalari (faqat shaxsiy chatda, faqat ADMIN_ID uchun).

Komandalar:
  /start        — yordam matni
  /guruhlar     — guruhlar ro'yxati va bugungi hisobot holati
  /hisobot      — bugungi umumiy holat
  /haftalik     — haftalik reyting darhol
  /vazifa       — interaktiv: guruh tanlash → vazifa matni (inline keyboard + FSM)
  /vaqt         — interaktiv: guruh tanlash → maydon tanlash → yangi vaqt
  /pauza <id>   — guruhni vaqtincha to'xtatish
  /faol <id>    — guruhni qayta yoqish
  /matn <id>    — guruhning bugungi to'liq hisobot matni
  /test_xulosa  — kunlik xulosani darhol tekshirish (debug)
  /bekor        — interaktiv jarayonni bekor qilish

Guruh tanlash inline keyboard orqali amalga oshiriladi.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import database as db
import texts
from config import Settings
from services import reporter
from services.scheduler import BotScheduler
from services.task_parser import TaskParser

logger = logging.getLogger(__name__)

router = Router(name="admin")

# Admin komandalari faqat shaxsiy chatda ishlaydi. Bu filtrsiz guruhda
# yozilgan /start ga bot "faqat admin uchun" deb javob berib, guruhni
# keraksiz xabar bilan to'ldirardi.
router.message.filter(F.chat.type == ChatType.PRIVATE)

# HH:MM formatini tekshirish uchun shablon
_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


# --------------------------------------------------------------------------
# FSM holatlari
# --------------------------------------------------------------------------

class VazifaSG(StatesGroup):
    """Vazifa qo'shish jarayoni."""
    text = State()  # guruh tanlangach, vazifa matnini kutamiz


class VaqtSG(StatesGroup):
    """Vaqtni o'zgartirish jarayoni."""
    field = State()  # guruh tanlangach, maydon (so'rov/ertalab) tanlanadi
    value = State()  # maydon tanlangach, yangi vaqt kutiladi


# --------------------------------------------------------------------------
# Yordamchilar
# --------------------------------------------------------------------------

def _is_admin_msg(message: Message, settings: Settings) -> bool:
    """Xabar admindan, shaxsiy chatdan kelganini tekshiradi."""
    if message.chat.type != ChatType.PRIVATE:
        return False
    return bool(message.from_user and message.from_user.id == settings.admin_id)


def _is_admin_cb(callback: CallbackQuery, settings: Settings) -> bool:
    """Callback admindan kelganini tekshiradi."""
    return bool(callback.from_user and callback.from_user.id == settings.admin_id)


def _groups_kb(groups: list[dict[str, Any]], prefix: str) -> InlineKeyboardMarkup:
    """Guruhlar ro'yxatidan inline keyboard tuzadi (callback: '<prefix>:<id>')."""
    rows = [
        [
            InlineKeyboardButton(
                text=f"[{g['id']}] {g.get('name') or 'nomsiz'}",
                callback_data=f"{prefix}:{g['id']}",
            )
        ]
        for g in groups
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --------------------------------------------------------------------------
# Oddiy komandalar
# --------------------------------------------------------------------------

@router.message(Command("start"))
async def cmd_start(message: Message, settings: Settings) -> None:
    """Yordam matnini ko'rsatadi."""
    if not _is_admin_msg(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    await message.answer(texts.ADMIN_START)


@router.message(Command("guruhlar", "gurular"))
async def cmd_groups(message: Message, settings: Settings) -> None:
    """Barcha guruhlar ro'yxati va bugungi hisobot holati."""
    if not _is_admin_msg(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    try:
        groups = await db.get_all_groups()
        if not groups:
            await message.answer(texts.NO_GROUPS)
            return
        date = reporter.today_str(settings.tz)
        reports = await db.get_reports_for_date(date)
        lines = [texts.group_list_line(g, int(g["id"]) in reports) for g in groups]
        await message.answer("📋 Guruhlar:\n\n" + "\n\n".join(lines))
    except Exception:
        logger.error("/guruhlar xatosi", exc_info=True)
        await message.answer("Xatolik yuz berdi. Loglarni tekshiring.")


@router.message(Command("hisobot"))
async def cmd_status(message: Message, settings: Settings) -> None:
    """Bugungi umumiy holatni ko'rsatadi."""
    if not _is_admin_msg(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    try:
        text = await reporter.build_daily_summary(settings.tz)
        await message.answer(text)
    except Exception:
        logger.error("/hisobot xatosi", exc_info=True)
        await message.answer("Xatolik yuz berdi. Loglarni tekshiring.")


@router.message(Command("haftalik"))
async def cmd_weekly(message: Message, settings: Settings) -> None:
    """Haftalik reytingni darhol tuzib beradi."""
    if not _is_admin_msg(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    try:
        text = await reporter.build_weekly_analysis(settings.tz)
        await message.answer(text)
    except Exception:
        logger.error("/haftalik xatosi", exc_info=True)
        await message.answer("Xatolik yuz berdi. Loglarni tekshiring.")


@router.message(Command("test_xulosa"))
async def cmd_test_summary(message: Message, settings: Settings) -> None:
    """Debug: kunlik xulosani darhol tuzib ko'rsatadi."""
    if not _is_admin_msg(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    try:
        text = await reporter.build_daily_summary(settings.tz)
        await message.answer("🧪 (test)\n\n" + text)
    except Exception:
        logger.error("/test_xulosa xatosi", exc_info=True)
        await message.answer("Xatolik yuz berdi. Loglarni tekshiring.")


@router.message(Command("bekor"))
async def cmd_cancel(message: Message, settings: Settings, state: FSMContext) -> None:
    """Interaktiv jarayonni bekor qiladi."""
    if not _is_admin_msg(message, settings):
        return
    await state.clear()
    await message.answer(texts.CANCELLED)


# --------------------------------------------------------------------------
# Debug komandalar — jadvalni kutmasdan qo'lda ishga tushirish
# --------------------------------------------------------------------------

@router.message(Command("debug"))
async def cmd_debug(message: Message, settings: Settings) -> None:
    """Debug komandalar ro'yxati."""
    if not _is_admin_msg(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    await message.answer(texts.DEBUG_HELP)


@router.message(Command("test_haftalik"))
async def cmd_test_weekly(
    message: Message, settings: Settings, scheduler: BotScheduler
) -> None:
    """Haftalik tahlilni adminga yuborish yo'lini sinaydi."""
    if not _is_admin_msg(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    await scheduler.trigger_weekly()
    await message.answer(texts.TEST_DONE)


@router.message(Command("test_ertalabki"))
async def cmd_test_morning(
    message: Message,
    command: CommandObject,
    settings: Settings,
    scheduler: BotScheduler,
) -> None:
    """Guruhga ertalabki xabarni qo'lda yuboradi."""
    if not _is_admin_msg(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    gid = _parse_group_id(command)
    if gid is None:
        await message.answer(texts.USAGE_TEST_MORNING)
        return
    if not await db.get_group_by_id(gid):
        await message.answer(texts.GROUP_NOT_FOUND)
        return
    await scheduler.trigger_morning(gid)
    await message.answer(texts.TEST_SENT_GROUP)


@router.message(Command("test_sorov"))
async def cmd_test_request(
    message: Message,
    command: CommandObject,
    settings: Settings,
    scheduler: BotScheduler,
) -> None:
    """Guruhga hisobot so'rovini qo'lda yuboradi."""
    if not _is_admin_msg(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    gid = _parse_group_id(command)
    if gid is None:
        await message.answer(texts.USAGE_TEST_REQUEST)
        return
    if not await db.get_group_by_id(gid):
        await message.answer(texts.GROUP_NOT_FOUND)
        return
    await scheduler.trigger_request(gid)
    await message.answer(texts.TEST_SENT_GROUP)


@router.message(Command("test_eslatma"))
async def cmd_test_reminders(
    message: Message, settings: Settings, scheduler: BotScheduler
) -> None:
    """Hozir hisobot bermaganlarga eslatma yuborishni sinaydi."""
    if not _is_admin_msg(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    await scheduler.trigger_reminders()
    await message.answer(texts.TEST_DONE)


# --------------------------------------------------------------------------
# /pauza, /faol, /matn — argumentli komandalar
# --------------------------------------------------------------------------

def _parse_group_id(command: CommandObject) -> int | None:
    """Komanda argumentidan guruh id ni ajratadi."""
    if not command.args:
        return None
    try:
        return int(command.args.strip().split()[0])
    except (ValueError, IndexError):
        return None


@router.message(Command("pauza"))
async def cmd_pause(
    message: Message,
    command: CommandObject,
    settings: Settings,
    scheduler: BotScheduler,
) -> None:
    """Guruhni vaqtincha to'xtatadi (joblari o'chiriladi)."""
    if not _is_admin_msg(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    gid = _parse_group_id(command)
    if gid is None:
        await message.answer(texts.USAGE_PAUZA)
        return
    group = await db.get_group_by_id(gid)
    if not group:
        await message.answer(texts.GROUP_NOT_FOUND)
        return
    await db.set_group_active(gid, False)
    scheduler.remove_group(gid)
    await message.answer(texts.group_paused(group.get("name") or f"Guruh {gid}"))


@router.message(Command("faol"))
async def cmd_activate(
    message: Message,
    command: CommandObject,
    settings: Settings,
    scheduler: BotScheduler,
) -> None:
    """Guruhni qayta faollashtiradi (joblari qayta tuziladi)."""
    if not _is_admin_msg(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    gid = _parse_group_id(command)
    if gid is None:
        await message.answer(texts.USAGE_FAOL)
        return
    group = await db.get_group_by_id(gid)
    if not group:
        await message.answer(texts.GROUP_NOT_FOUND)
        return
    await db.set_group_active(gid, True)
    group = await db.get_group_by_id(gid)  # yangilangan holat
    if group:
        scheduler.schedule_group(group)
    await message.answer(texts.group_activated(group.get("name") or f"Guruh {gid}"))


@router.message(Command("matn"))
async def cmd_report_text(
    message: Message,
    command: CommandObject,
    settings: Settings,
) -> None:
    """Guruhning bugungi to'liq hisobot matnini ko'rsatadi."""
    if not _is_admin_msg(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    gid = _parse_group_id(command)
    if gid is None:
        await message.answer(texts.USAGE_MATN)
        return
    group = await db.get_group_by_id(gid)
    if not group:
        await message.answer(texts.GROUP_NOT_FOUND)
        return
    date = reporter.today_str(settings.tz)
    report = await db.get_latest_report(gid, date)
    await message.answer(
        texts.report_text_view(group.get("name") or f"Guruh {gid}", report)
    )


# --------------------------------------------------------------------------
# /vazifa — interaktiv (guruh tanlash → vazifa matni)
# --------------------------------------------------------------------------

@router.message(Command("vazifa"))
async def cmd_vazifa(message: Message, settings: Settings) -> None:
    """Vazifa qo'shish: guruh tanlash keyboardini yuboradi."""
    if not _is_admin_msg(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    groups = await db.get_all_groups(only_active=True)
    if not groups:
        await message.answer(texts.NO_GROUPS)
        return
    await message.answer(texts.CHOOSE_GROUP, reply_markup=_groups_kb(groups, "vz"))


@router.callback_query(lambda c: c.data and c.data.startswith("vz:"))
async def cb_vazifa_group(
    callback: CallbackQuery, settings: Settings, state: FSMContext
) -> None:
    """Guruh tanlandi — vazifa matnini kutamiz."""
    if not _is_admin_cb(callback, settings):
        await callback.answer()
        return
    gid = int(callback.data.split(":", 1)[1])
    await state.update_data(group_id=gid)
    await state.set_state(VazifaSG.text)
    await callback.message.edit_text(texts.VAZIFA_ENTER)
    await callback.answer()


@router.message(VazifaSG.text)
async def on_vazifa_text(
    message: Message, settings: Settings, state: FSMContext
) -> None:
    """Vazifa matnini qabul qilib bazaga yozadi."""
    if not _is_admin_msg(message, settings):
        return
    data = await state.get_data()
    gid = int(data["group_id"])
    date = reporter.today_str(settings.tz)

    # Har bir bo'sh bo'lmagan qatorni alohida vazifa deb qabul qilamiz
    lines = [ln.strip() for ln in (message.text or "").splitlines() if ln.strip()]
    for line in lines:
        await db.add_task(gid, date, line)

    await state.clear()
    group = await db.get_group_by_id(gid)
    name = group.get("name") if group else f"Guruh {gid}"
    await message.answer(texts.vazifa_added(name or f"Guruh {gid}", len(lines)))


# --------------------------------------------------------------------------
# /vaqt — interaktiv (guruh → maydon → yangi vaqt)
# --------------------------------------------------------------------------

@router.message(Command("vaqt"))
async def cmd_vaqt(message: Message, settings: Settings) -> None:
    """Vaqtni o'zgartirish: guruh tanlash keyboardini yuboradi."""
    if not _is_admin_msg(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    groups = await db.get_all_groups(only_active=True)
    if not groups:
        await message.answer(texts.NO_GROUPS)
        return
    await message.answer(texts.CHOOSE_GROUP, reply_markup=_groups_kb(groups, "vq"))


@router.callback_query(lambda c: c.data and c.data.startswith("vq:"))
async def cb_vaqt_group(
    callback: CallbackQuery, settings: Settings, state: FSMContext
) -> None:
    """Guruh tanlandi — qaysi vaqtni o'zgartirishni so'raymiz."""
    if not _is_admin_cb(callback, settings):
        await callback.answer()
        return
    gid = int(callback.data.split(":", 1)[1])
    await state.update_data(group_id=gid)
    await state.set_state(VaqtSG.field)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.VAQT_FIELD_REQUEST, callback_data="vqf:request_time")],
            [InlineKeyboardButton(text=texts.VAQT_FIELD_MORNING, callback_data="vqf:morning_time")],
        ]
    )
    await callback.message.edit_text(texts.VAQT_CHOOSE_FIELD, reply_markup=kb)
    await callback.answer()


@router.callback_query(VaqtSG.field, lambda c: c.data and c.data.startswith("vqf:"))
async def cb_vaqt_field(
    callback: CallbackQuery, settings: Settings, state: FSMContext
) -> None:
    """Maydon tanlandi — yangi vaqtni kutamiz."""
    if not _is_admin_cb(callback, settings):
        await callback.answer()
        return
    field = callback.data.split(":", 1)[1]
    await state.update_data(field=field)
    await state.set_state(VaqtSG.value)
    await callback.message.edit_text(texts.VAQT_ENTER)
    await callback.answer()


@router.message(VaqtSG.value)
async def on_vaqt_value(
    message: Message,
    settings: Settings,
    state: FSMContext,
    scheduler: BotScheduler,
) -> None:
    """Yangi vaqtni tekshirib, bazaga yozadi va jobni qayta rejalashtiradi."""
    if not _is_admin_msg(message, settings):
        return
    raw = (message.text or "").strip()
    match = _TIME_RE.match(raw)
    if not match:
        await message.answer(texts.VAQT_INVALID)  # holatda qolamiz, qayta urinsin
        return

    value = f"{int(match.group(1)):02d}:{match.group(2)}"  # HH:MM normallash
    data = await state.get_data()
    gid = int(data["group_id"])
    field = data["field"]

    await db.update_group_time(gid, field, value)
    group = await db.get_group_by_id(gid)
    if group:
        scheduler.reschedule_group(group)  # yangi vaqt bilan job qayta tuziladi

    await state.clear()
    label = texts.VAQT_FIELD_REQUEST if field == "request_time" else texts.VAQT_FIELD_MORNING
    name = (group.get("name") if group else None) or f"Guruh {gid}"
    await message.answer(texts.vaqt_updated(name, label, value))


# --------------------------------------------------------------------------
# /doimiy — doimiy (takrorlanuvchi) vazifalar ro'yxati
# --------------------------------------------------------------------------

@router.message(Command("doimiy"))
async def cmd_recurring(message: Message, settings: Settings) -> None:
    """Barcha guruhlarning doimiy vazifalarini ko'rsatadi."""
    if not _is_admin_msg(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    try:
        groups = await db.get_all_groups()
        nomlar = {int(g["id"]): (g.get("name") or f"Guruh {g['id']}") for g in groups}
        hammasi = await db.get_recurring_tasks()
        if not hammasi:
            await message.answer(texts.DOIMIY_YOQ)
            return

        bloklar: list[str] = []
        tugmalar: list[list[InlineKeyboardButton]] = []
        for gid, nomi in nomlar.items():
            guruh_vazifalari = [v for v in hammasi if int(v["group_id"]) == gid]
            if not guruh_vazifalari:
                continue
            bloklar.append(texts.doimiy_royxat(nomi, guruh_vazifalari))
            for v in guruh_vazifalari:
                tugmalar.append([
                    InlineKeyboardButton(
                        text=f"🗑 [{v['id']}] {v['text'][:30]}",
                        callback_data=f"rmrec:{v['id']}",
                    )
                ])

        await message.answer(
            "\n\n".join(bloklar),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=tugmalar),
        )
    except Exception:
        logger.error("/doimiy xatosi", exc_info=True)
        await message.answer("Xatolik yuz berdi. Loglarni tekshiring.")


@router.callback_query(lambda c: c.data and c.data.startswith("rmrec:"))
async def cb_remove_recurring(callback: CallbackQuery, settings: Settings) -> None:
    """Doimiy vazifani o'chiradi."""
    if not _is_admin_cb(callback, settings):
        await callback.answer()
        return
    try:
        task_id = int(callback.data.split(":", 1)[1])
        hammasi = await db.get_recurring_tasks()
        matn = next((v["text"] for v in hammasi if int(v["id"]) == task_id), "")
        await db.delete_recurring_task(task_id)
        await callback.message.answer(texts.doimiy_ochirildi(matn or f"#{task_id}"))
    except Exception:
        logger.error("Doimiy vazifani o'chirishda xato", exc_info=True)
    await callback.answer()


# --------------------------------------------------------------------------
# Erkin matn bilan vazifa berish
#
# Bu handler eng oxirida turishi SHART: u komanda bo'lmagan har qanday
# matnni ushlaydi. Undan oldingi handlerlar (komandalar va FSM holatlari)
# birinchi tekshiriladi.
# --------------------------------------------------------------------------

def _tasdiq_klaviaturasi() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=texts.TASDIQLASH, callback_data="nlok"),
        InlineKeyboardButton(text=texts.BEKOR_QILISH, callback_data="nlbekor"),
    ]])


@router.message(StateFilter(None), F.text & ~F.text.startswith("/"))
async def on_free_text(
    message: Message,
    settings: Settings,
    state: FSMContext,
    task_parser: TaskParser,
) -> None:
    """Admin oddiy gap bilan yozgan vazifalarni tushunadi."""
    if not _is_admin_msg(message, settings):
        return
    if not task_parser.enabled:
        await message.answer(texts.AI_OCHIQ_EMAS)
        return

    try:
        groups = await db.get_all_groups(only_active=True)
        if not groups:
            await message.answer(texts.NO_GROUPS)
            return

        kutish = await message.answer(texts.TAHLIL_QILINMOQDA)
        natija = await task_parser.parse(message.text or "", groups, settings.tz)

        if natija is None or not natija["tushunarli"]:
            savol = (natija or {}).get("savol") or ""
            await kutish.edit_text(savol or texts.TUSHUNMADIM)
            return

        nomlar = {int(g["id"]): (g.get("name") or f"Guruh {g['id']}") for g in groups}
        bloklar = [
            texts.tasdiq_bloki(
                nomlar.get(t["guruh_id"], f"Guruh {t['guruh_id']}"),
                t["tur"], t["sana"], t["hafta_kunlari"], t["vazifalar"],
            )
            for t in natija["topshiriqlar"]
        ]
        await state.update_data(nl_topshiriqlar=natija["topshiriqlar"])
        await kutish.edit_text(
            texts.tasdiq_sorovi(bloklar), reply_markup=_tasdiq_klaviaturasi()
        )
    except Exception:
        logger.error("Erkin matnni tahlil qilishda xato", exc_info=True)
        await message.answer("Xatolik yuz berdi. Loglarni tekshiring.")


@router.callback_query(lambda c: c.data == "nlok")
async def cb_confirm_tasks(
    callback: CallbackQuery, settings: Settings, state: FSMContext
) -> None:
    """Tasdiqlangan vazifalarni bazaga yozadi."""
    if not _is_admin_cb(callback, settings):
        await callback.answer()
        return
    try:
        data = await state.get_data()
        topshiriqlar = data.get("nl_topshiriqlar") or []
        if not topshiriqlar:
            await callback.message.edit_text(texts.CANCELLED)
            await callback.answer()
            return

        bir_martalik = 0
        doimiy = 0
        for t in topshiriqlar:
            gid = int(t["guruh_id"])
            if t["tur"] == "doimiy":
                for v in t["vazifalar"]:
                    await db.add_recurring_task(gid, v, t["hafta_kunlari"], settings.tz)
                    doimiy += 1
            else:
                for v in t["vazifalar"]:
                    await db.add_task(gid, t["sana"], v)
                    bir_martalik += 1

        await state.update_data(nl_topshiriqlar=None)
        await callback.message.edit_text(
            texts.vazifalar_saqlandi(bir_martalik, doimiy)
        )
    except Exception:
        logger.error("Vazifalarni saqlashda xato", exc_info=True)
        await callback.message.answer("Xatolik yuz berdi. Loglarni tekshiring.")
    await callback.answer()


@router.callback_query(lambda c: c.data == "nlbekor")
async def cb_cancel_tasks(
    callback: CallbackQuery, settings: Settings, state: FSMContext
) -> None:
    """Tahlil natijasini bekor qiladi."""
    if not _is_admin_cb(callback, settings):
        await callback.answer()
        return
    await state.update_data(nl_topshiriqlar=None)
    await callback.message.edit_text(texts.CANCELLED)
    await callback.answer()
