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


# --------------------------------------------------------------------------
# Vazifa nazorati va rasm xulosada
# --------------------------------------------------------------------------

async def test_xulosada_bajarilmagan_vazifa_korinadi(database, group_id):
    """Admin qaysi vazifa qolib ketganini xulosaning o'zidan bilishi kerak."""
    rid = await database.add_report(
        group_id=group_id, user_id=1, user_name="Ali",
        date=_today(), raw_text="Matn", tz=TZ,
    )
    await database.update_report_ai(
        report_id=rid, status="accepted", ai_score=4,
        ai_summary="Ish davom etmoqda", missing_parts=[],
        has_problem=False, problem_text="",
        done_tasks=["devor suvash", "pol tayyorlash"],
        undone_tasks=["elektr chizmasini tekshirish"],
    )
    text = await reporter.build_daily_summary(TZ)

    assert "3 tadan 2 tasi bajarildi" in text
    assert "❌ elektr chizmasini tekshirish" in text


async def test_hamma_vazifa_bajarilsa_xatolik_qatori_yoq(database, group_id):
    rid = await database.add_report(
        group_id=group_id, user_id=1, user_name="Ali",
        date=_today(), raw_text="Matn", tz=TZ,
    )
    await database.update_report_ai(
        report_id=rid, status="accepted", ai_score=5, ai_summary="Hammasi tayyor",
        missing_parts=[], has_problem=False, problem_text="",
        done_tasks=["devor suvash"], undone_tasks=[],
    )
    text = await reporter.build_daily_summary(TZ)
    assert "1 tadan 1 tasi bajarildi" in text
    assert "❌" not in text


async def test_vazifa_belgilanmagan_bolsa_qator_qoshilmaydi(database, group_id):
    """Vazifa berilmagan kunlarda xulosa avvalgidek sodda qolishi kerak."""
    rid = await database.add_report(
        group_id=group_id, user_id=1, user_name="Ali",
        date=_today(), raw_text="Matn", tz=TZ,
    )
    await database.update_report_ai(
        report_id=rid, status="accepted", ai_score=4, ai_summary="Xulosa",
        missing_parts=[], has_problem=False, problem_text="",
        done_tasks=[], undone_tasks=[],
    )
    text = await reporter.build_daily_summary(TZ)
    assert "bajarildi" not in text


async def test_eski_hisobotlar_xulosani_buzmaydi(database, group_id):
    """
    Migratsiyadan oldingi hisobotlarda done_tasks NULL bo'ladi —
    xulosa baribir tuzilishi kerak.
    """
    await database.add_report(
        group_id=group_id, user_id=1, user_name="Ali",
        date=_today(), raw_text="Eski hisobot", tz=TZ,
    )
    text = await reporter.build_daily_summary(TZ)
    assert "Hisobot berdi: 1/1" in text


async def test_rasmli_hisobot_belgilanadi(database, group_id):
    await database.add_report(
        group_id=group_id, user_id=1, user_name="Ali",
        date=_today(), raw_text="Tozalik bajarildi", has_photo=True, tz=TZ,
    )
    assert "📷" in await reporter.build_daily_summary(TZ)


# --------------------------------------------------------------------------
# Savollar uchun kontekst
# --------------------------------------------------------------------------

async def test_kontekstda_guruh_vazifa_va_hisobot_bor(database, group_id):
    bugun = _today()
    await database.add_task(group_id, bugun, "devor suvash")
    await database.add_recurring_task(group_id, "xavfsizlik tekshiruvi", tz=TZ)
    rid = await database.add_report(
        group_id=group_id, user_id=1, user_name="Ali",
        date=bugun, raw_text="Devor suvash tugadi", tz=TZ,
    )
    await database.update_report_ai(
        report_id=rid, status="accepted", ai_score=4,
        ai_summary="Devor suvash bajarildi", missing_parts=[],
        has_problem=True, problem_text="Sement kam",
        done_tasks=["devor suvash"], undone_tasks=["elektr"],
    )

    kontekst = await reporter.build_assistant_context(TZ)

    assert "Test guruh" in kontekst
    assert "devor suvash" in kontekst
    assert "xavfsizlik tekshiruvi" in kontekst
    assert "Devor suvash bajarildi" in kontekst
    assert "MUAMMO: Sement kam" in kontekst
    assert "Bajarilmagan vazifalar: elektr" in kontekst
    assert "baho 4/5" in kontekst


async def test_kontekstda_hisobot_yoqligi_korinadi(database, group_id):
    kontekst = await reporter.build_assistant_context(TZ)
    assert "Bugungi hisobot: YO'Q" in kontekst


async def test_kontekst_uzun_hisobotni_qisqartiradi(database, group_id):
    """Kontekst modelga boradi — juda uzun matn kesilishi kerak."""
    await database.add_report(
        group_id=group_id, user_id=1, user_name="Ali",
        date=_today(), raw_text="A" * 2000, tz=TZ,
    )
    kontekst = await reporter.build_assistant_context(TZ)
    assert "A" * 400 in kontekst
    assert "A" * 500 not in kontekst
    assert "..." in kontekst


async def test_kontekstda_pauzadagi_guruh_ham_bor(database, group_id):
    """Admin pauzadagi guruh haqida ham so'rashi mumkin."""
    await database.set_group_active(group_id, False)
    kontekst = await reporter.build_assistant_context(TZ)
    assert "pauzada" in kontekst
