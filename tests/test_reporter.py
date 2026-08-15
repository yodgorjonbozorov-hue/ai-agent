"""
test_reporter.py — kunlik xulosa, eslatma ro'yxati va haftalik tahlil testlari.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from services import reporter

TZ = ZoneInfo("Asia/Tashkent")


def _today() -> str:
    return reporter.today_str(TZ)


def _days_ago(n: int) -> str:
    return (datetime.now(TZ).date() - timedelta(days=n)).strftime("%Y-%m-%d")


# --------------------------------------------------------------------------
# Kunlik xulosa
# --------------------------------------------------------------------------

async def test_xulosada_hisobot_bermaganlar_belgilanadi(database, group_id):
    text = await reporter.build_daily_summary(TZ)
    assert "Hisobot berdi: 0/1" in text
    assert "❌ Test guruh" in text


async def test_xulosada_ai_qisqa_xulosasi_korinadi(database, group_id):
    report_id = await database.add_report(
        group_id=group_id, user_id=1, user_name="Ali",
        date=_today(), raw_text="Matn", tz=TZ,
    )
    await database.update_report_ai(
        report_id=report_id, status="accepted", ai_score=5,
        ai_summary="3 ta obyekt yakunlandi", missing_parts=[],
        has_problem=False, problem_text="",
    )
    text = await reporter.build_daily_summary(TZ)
    assert "Hisobot berdi: 1/1" in text
    assert "3 ta obyekt yakunlandi" in text
    assert "✅" in text


async def test_muammoli_hisobot_etibor_bolimiga_tushadi(database, group_id):
    report_id = await database.add_report(
        group_id=group_id, user_id=1, user_name="Ali",
        date=_today(), raw_text="Matn", tz=TZ,
    )
    await database.update_report_ai(
        report_id=report_id, status="accepted", ai_score=3,
        ai_summary="Ish davom etmoqda", missing_parts=[],
        has_problem=True, problem_text="Sement yetishmayapti",
    )
    text = await reporter.build_daily_summary(TZ)
    assert "E'tibor talab qiladi" in text
    assert "Sement yetishmayapti" in text
    assert "⚠️" in text


async def test_pauzadagi_guruh_xulosaga_tushmaydi(database, group_id):
    await database.set_group_active(group_id, False)
    text = await reporter.build_daily_summary(TZ)
    assert "Hisobot berdi: 0/0" in text
    assert "Test guruh" not in text


# --------------------------------------------------------------------------
# Eslatma ro'yxati
# --------------------------------------------------------------------------

async def test_sorov_yuborilmagan_guruhga_eslatma_kelmaydi(database, group_id):
    """18:00 so'rovi hali yuborilmagan guruhni bezovta qilmaymiz."""
    assert await reporter.missing_groups_today(TZ) == []


async def test_sorovdan_keyin_javob_bermagan_guruh_royxatda(database, group_id):
    await database.add_log(group_id, _today(), "request", TZ)
    missing = await reporter.missing_groups_today(TZ)
    assert [g["id"] for g in missing] == [group_id]


async def test_hisobot_berganga_eslatma_yuborilmaydi(database, group_id):
    await database.add_log(group_id, _today(), "request", TZ)
    await database.add_report(
        group_id=group_id, user_id=1, user_name="Ali",
        date=_today(), raw_text="Hisobot matni", tz=TZ,
    )
    assert await reporter.missing_groups_today(TZ) == []


# --------------------------------------------------------------------------
# Haftalik tahlil
# --------------------------------------------------------------------------

async def test_haftalik_foiz_va_ortacha_baho(database, group_id):
    """3 kun so'rov yuborilgan, 2 kunga hisobot berilgan → 67%."""
    for n in (0, 1, 2):
        await database.add_log(group_id, _days_ago(n), "request", TZ)

    for n, score in ((0, 5), (1, 3)):
        rid = await database.add_report(
            group_id=group_id, user_id=1, user_name="Ali",
            date=_days_ago(n), raw_text="Matn", tz=TZ,
        )
        await database.update_report_ai(
            report_id=rid, status="accepted", ai_score=score,
            ai_summary="", missing_parts=[], has_problem=False, problem_text="",
        )

    text = await reporter.build_weekly_analysis(TZ)
    assert "67%" in text
    assert "4.0/5" in text  # (5 + 3) / 2
    assert "🥇" in text


async def test_haftalik_malumot_yoq_holati(database, group_id):
    text = await reporter.build_weekly_analysis(TZ)
    assert "Haftalik tahlil" in text
    assert "0%" in text


async def test_haftalik_takrorlanuvchi_muammolar(database, group_id):
    await database.add_log(group_id, _today(), "request", TZ)
    rid = await database.add_report(
        group_id=group_id, user_id=1, user_name="Ali",
        date=_today(), raw_text="Matn", tz=TZ,
    )
    await database.update_report_ai(
        report_id=rid, status="accepted", ai_score=3, ai_summary="",
        missing_parts=[], has_problem=True, problem_text="Kran ishlamayapti",
    )
    text = await reporter.build_weekly_analysis(TZ)
    assert "Takrorlanuvchi muammolar" in text
    assert "Kran ishlamayapti" in text


async def test_hafta_oynasi_eski_hisobotlarni_olmaydi(database, group_id):
    """8 kun oldingi hisobot 7 kunlik oynaga tushmasligi kerak."""
    await database.add_log(group_id, _days_ago(8), "request", TZ)
    await database.add_report(
        group_id=group_id, user_id=1, user_name="Ali",
        date=_days_ago(8), raw_text="Eski hisobot", tz=TZ,
    )
    text = await reporter.build_weekly_analysis(TZ)
    assert "0%" in text
