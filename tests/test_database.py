"""
test_database.py — baza qatlamining CRUD funksiyalari testlari.
"""

from __future__ import annotations

import json
from zoneinfo import ZoneInfo

import pytest

TZ = ZoneInfo("Asia/Tashkent")
DATE = "2026-03-10"


# --------------------------------------------------------------------------
# groups
# --------------------------------------------------------------------------

async def test_guruh_qoshiladi_va_topiladi(database, group_id):
    group = await database.get_group_by_chat_id(-1001234567890)
    assert group is not None
    assert group["id"] == group_id
    assert group["name"] == "Test guruh"
    assert group["is_active"] == 1
    # Standart vaqtlar
    assert group["request_time"] == "18:00"
    assert group["morning_time"] == "09:00"


async def test_qayta_qoshilsa_yangi_guruh_yaratilmaydi(database, group_id):
    """Bot guruhdan chiqib qayta qo'shilsa, dublikat yozuv paydo bo'lmasligi kerak."""
    again = await database.add_or_update_group(
        chat_id=-1001234567890, name="Yangi nom", tz=TZ
    )
    assert again == group_id
    groups = await database.get_all_groups()
    assert len(groups) == 1
    assert groups[0]["name"] == "Yangi nom"


async def test_pauza_va_qayta_faollashtirish(database, group_id):
    await database.set_group_active(group_id, False)
    assert (await database.get_group_by_id(group_id))["is_active"] == 0
    assert await database.get_all_groups(only_active=True) == []

    await database.set_group_active(group_id, True)
    assert len(await database.get_all_groups(only_active=True)) == 1


async def test_vaqt_yangilanadi(database, group_id):
    await database.update_group_time(group_id, "request_time", "19:30")
    assert (await database.get_group_by_id(group_id))["request_time"] == "19:30"


async def test_notogri_vaqt_maydoni_rad_etiladi(database, group_id):
    """SQL injection'ning oldini olish uchun maydon nomi oq ro'yxatda."""
    with pytest.raises(ValueError):
        await database.update_group_time(group_id, "name; DROP TABLE groups", "19:30")


# --------------------------------------------------------------------------
# tasks
# --------------------------------------------------------------------------

async def test_vazifalar_sana_boyicha_ajratiladi(database, group_id):
    await database.add_task(group_id, DATE, "Birinchi vazifa")
    await database.add_task(group_id, DATE, "Ikkinchi vazifa")
    await database.add_task(group_id, "2026-03-11", "Ertangi vazifa")

    bugun = await database.get_tasks(group_id, DATE)
    assert [t["text"] for t in bugun] == ["Birinchi vazifa", "Ikkinchi vazifa"]


# --------------------------------------------------------------------------
# reports
# --------------------------------------------------------------------------

async def test_hisobot_saqlanadi_va_oqiladi(database, group_id):
    report_id = await database.add_report(
        group_id=group_id, user_id=42, user_name="Ali",
        date=DATE, raw_text="Bugun 3 ta obyekt yakunlandi.", tz=TZ,
    )
    report = await database.get_latest_report(group_id, DATE)
    assert report["id"] == report_id
    assert report["status"] == "pending"
    assert report["user_name"] == "Ali"


async def test_ai_natijasi_yozilib_oqiladi(database, group_id):
    report_id = await database.add_report(
        group_id=group_id, user_id=42, user_name="Ali",
        date=DATE, raw_text="Matn", tz=TZ,
    )
    await database.update_report_ai(
        report_id=report_id, status="accepted", ai_score=4,
        ai_summary="Yaxshi hisobot", missing_parts=["ertangi reja"],
        has_problem=True, problem_text="Materiyal yetishmayapti",
    )
    report = await database.get_latest_report(group_id, DATE)
    assert report["status"] == "accepted"
    assert report["ai_score"] == 4
    assert report["has_problem"] == 1
    # missing_parts JSON sifatida saqlanadi — o'zbekcha harflar buzilmasligi kerak
    assert json.loads(report["missing_parts"]) == ["ertangi reja"]


async def test_kunlik_hisobotlarda_oxirgisi_asosiy(database, group_id):
    """Bir kunda bir necha hisobot kelsa, xulosaga eng oxirgisi tushadi."""
    await database.add_report(
        group_id=group_id, user_id=1, user_name="Ali",
        date=DATE, raw_text="Birinchi urinish", tz=TZ,
    )
    second = await database.add_report(
        group_id=group_id, user_id=1, user_name="Ali",
        date=DATE, raw_text="To'ldirilgan hisobot", tz=TZ,
    )
    latest = await database.get_latest_report(group_id, DATE)
    assert latest["id"] == second

    hammasi = await database.get_reports_for_date(DATE)
    assert hammasi[group_id]["raw_text"] == "To'ldirilgan hisobot"


async def test_hisobot_yoq_kun(database, group_id):
    assert await database.get_latest_report(group_id, DATE) is None
    assert await database.get_reports_for_date(DATE) == {}


async def test_oraliq_boyicha_hisobotlar(database, group_id):
    for date in ("2026-03-08", "2026-03-09", "2026-03-15"):
        await database.add_report(
            group_id=group_id, user_id=1, user_name="Ali",
            date=date, raw_text="Matn", tz=TZ,
        )
    oraliq = await database.get_reports_range("2026-03-08", "2026-03-10")
    assert [r["date"] for r in oraliq] == ["2026-03-08", "2026-03-09"]


# --------------------------------------------------------------------------
# logs
# --------------------------------------------------------------------------

async def test_log_yozilib_tekshiriladi(database, group_id):
    assert await database.has_log(group_id, DATE, "request") is False
    await database.add_log(group_id, DATE, "request", TZ)
    assert await database.has_log(group_id, DATE, "request") is True
    # Boshqa tur va boshqa sana ta'sirlanmaydi
    assert await database.has_log(group_id, DATE, "reminder_soft") is False
    assert await database.has_log(group_id, "2026-03-11", "request") is False


async def test_umumiy_log_group_id_siz(database):
    """Kunlik xulosa kabi loglar group_id = NULL bilan yoziladi."""
    await database.add_log(None, DATE, "daily_summary", TZ)
    assert await database.has_log(None, DATE, "daily_summary") is True


async def test_sorov_kunlari_oraliqda(database, group_id):
    await database.add_log(group_id, "2026-03-09", "request", TZ)
    await database.add_log(group_id, "2026-03-10", "request", TZ)
    await database.add_log(group_id, "2026-03-10", "reminder_soft", TZ)

    kunlar = await database.get_log_dates_range("2026-03-09", "2026-03-10", "request")
    assert sorted(d for _, d in kunlar) == ["2026-03-09", "2026-03-10"]


# --------------------------------------------------------------------------
# Migratsiya — ishlab turgan bazaga yangi ustun qo'shish
# --------------------------------------------------------------------------

ESKI_SXEMA = """
CREATE TABLE groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER UNIQUE NOT NULL,
    name TEXT, department TEXT, request_time TEXT NOT NULL DEFAULT '18:00',
    morning_time TEXT NOT NULL DEFAULT '09:00',
    is_active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT, group_id INTEGER NOT NULL,
    date TEXT NOT NULL, text TEXT NOT NULL);
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT, group_id INTEGER NOT NULL,
    user_id INTEGER, user_name TEXT, date TEXT NOT NULL, raw_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', ai_score INTEGER, ai_summary TEXT,
    missing_parts TEXT, has_problem INTEGER NOT NULL DEFAULT 0,
    problem_text TEXT, created_at TEXT NOT NULL);
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, group_id INTEGER, date TEXT NOT NULL,
    type TEXT NOT NULL, created_at TEXT NOT NULL);
"""


async def test_eski_baza_yangilanadi_va_malumot_saqlanadi(tmp_path):
    """
    Serverda allaqachon ishlab turgan baza yangi ustunlarni olishi va
    eski ma'lumot buzilmasligi kerak.
    """
    import aiosqlite
    import database as real_db

    yol = str(tmp_path / "eski.db")
    async with aiosqlite.connect(yol) as db:
        await db.executescript(ESKI_SXEMA)
        await db.execute(
            "INSERT INTO groups (chat_id, name, created_at) VALUES (?, ?, ?)",
            (-100777, "Eski guruh", "2026-01-01T00:00:00"),
        )
        await db.execute(
            "INSERT INTO reports (group_id, date, raw_text, created_at) "
            "VALUES (?, ?, ?, ?)",
            (1, "2026-01-01", "Eski hisobot matni", "2026-01-01T18:00:00"),
        )
        await db.commit()

    # Bot ishga tushgandagidek init_db chaqiramiz
    await real_db.init_db(yol)

    try:
        # Eski ma'lumot joyida
        guruhlar = await real_db.get_all_groups()
        assert [g["name"] for g in guruhlar] == ["Eski guruh"]
        hisobot = await real_db.get_latest_report(1, "2026-01-01")
        assert hisobot["raw_text"] == "Eski hisobot matni"

        # Yangi ustunlar qo'shilgan va bo'sh
        assert hisobot["done_tasks"] is None
        assert hisobot["undone_tasks"] is None
        assert hisobot["has_photo"] == 0

        # Yangi jadval ham yaratilgan
        assert await real_db.get_recurring_tasks(1) == []

        # Yangi ustunlarga yozib bo'ladi
        await real_db.update_report_ai(
            report_id=hisobot["id"], status="accepted", ai_score=4,
            ai_summary="xulosa", missing_parts=[], has_problem=False,
            problem_text="", done_tasks=["birinchi"], undone_tasks=["ikkinchi"],
        )
        yangilangan = await real_db.get_latest_report(1, "2026-01-01")
        assert json.loads(yangilangan["done_tasks"]) == ["birinchi"]
        assert json.loads(yangilangan["undone_tasks"]) == ["ikkinchi"]
    finally:
        real_db.set_db_path("data/bot.db")


async def test_migratsiya_takroriy_chaqiruvga_chidamli(tmp_path):
    """init_db har safar ishga tushganda chaqiriladi — xato bermasligi kerak."""
    import database as real_db
    yol = str(tmp_path / "takror.db")
    await real_db.init_db(yol)
    await real_db.init_db(yol)
    await real_db.init_db(yol)
    real_db.set_db_path("data/bot.db")
