"""
test_texts_and_scheduler.py — matn shablonlari va vaqt ajratish testlari.

Matnlar foydalanuvchiga ko'rinadi, shuning uchun ular hech qachon xato
(masalan `None` yoki bo'sh) bermasligi kerak.
"""

from __future__ import annotations

import re

import texts
from services.scheduler import _parse_hm

# Lotin o'zbek matnida kirill harflari bo'lmasligi kerak
CYRILLIC = re.compile(r"[Ѐ-ӿ]")


# --------------------------------------------------------------------------
# Matn shablonlari
# --------------------------------------------------------------------------

def test_ertalabki_xabarda_vazifalar_raqamlanadi():
    text = texts.morning_with_tasks(["Devor suvash", "Elektr chizmasi"])
    assert "1. Devor suvash" in text
    assert "2. Elektr chizmasi" in text


def test_toliqsiz_hisobot_javobida_yetishmagan_qism_bor():
    assert "ertangi reja" in texts.report_incomplete(["ertangi reja"])


def test_toliqsiz_hisobot_bosh_royxat_bilan_ham_ishlaydi():
    """AI yetishmagan qismlarni qaytarmasa ham javob mazmunli bo'lishi kerak."""
    text = texts.report_incomplete([])
    assert "ba'zi qismlar" in text


def test_kunlik_xulosa_bosh_royxat_bilan():
    text = texts.admin_daily_summary(
        date_str="10.03.2026", submitted=0, total=0, lines=[], attention=[],
    )
    assert "Hech qanday guruh" in text
    assert "E'tibor talab qiladi" not in text


def test_eskalatsiya_hammasi_javob_berganda():
    assert "Barcha guruhlar" in texts.admin_escalation([])


def test_hisobot_matni_yoq_holati():
    assert "bugun hisobot yo'q" in texts.report_text_view("Test guruh", None)


def test_hisobot_matni_korsatiladi():
    text = texts.report_text_view("Test guruh", {
        "status": "accepted", "ai_score": 4,
        "user_name": "Ali", "raw_text": "Bugun 3 ta obyekt yakunlandi.",
    })
    assert "Ali" in text
    assert "qabul qilingan" in text
    assert "Baho: 4/5" in text
    assert "Bugun 3 ta obyekt yakunlandi." in text


def test_haftalik_qatorida_baho_yoq_holati():
    """AI o'chirilgan bo'lsa baho yo'q — qator baribir tuzilishi kerak."""
    line = texts.weekly_group_line(1, "Test guruh", 80, None)
    assert "🥇" in line
    assert "80%" in line
    assert "—" in line


def test_haftalik_reytingda_medalsiz_orinlar():
    assert texts.weekly_group_line(4, "Guruh", 50, 3.0).startswith("4.")


def test_matnlarda_kirill_harflari_yoq():
    """Lotin o'zbekchada tasodifiy kirill harflari qolib ketmasligi kerak."""
    for name in dir(texts):
        value = getattr(texts, name)
        if isinstance(value, str) and not name.startswith("__"):
            assert not CYRILLIC.search(value), f"{name} da kirill harfi bor"


# --------------------------------------------------------------------------
# Vaqt ajratish
# --------------------------------------------------------------------------

def test_vaqt_togri_ajratiladi():
    assert _parse_hm("18:00", (0, 0)) == (18, 0)
    assert _parse_hm("09:30", (0, 0)) == (9, 30)


def test_buzuq_vaqt_standartga_tushadi():
    """Bazada buzuq vaqt bo'lsa ham scheduler yiqilmasligi kerak."""
    assert _parse_hm("kechqurun", (18, 0)) == (18, 0)
    assert _parse_hm("", (9, 0)) == (9, 0)
    assert _parse_hm(None, (9, 0)) == (9, 0)


# --------------------------------------------------------------------------
# Erkin matn javoblari
# --------------------------------------------------------------------------

def test_tushunmadim_guruh_nomlarini_korsatadi():
    """Foydalanuvchi qanday yozishni bilishi uchun guruh nomlari ko'rsatiladi."""
    matn = texts.tushunmadim("", ["Disney Kunlik Hisobot operator", "Topshiriqlar"])
    assert "Disney Kunlik Hisobot operator" in matn
    assert "Topshiriqlar" in matn


def test_tushunmadim_modelning_savolini_saqlaydi():
    matn = texts.tushunmadim("Qaysi guruhga: Topshiriqlar yoki Disney?", ["A", "B"])
    assert matn.startswith("Qaysi guruhga: Topshiriqlar yoki Disney?")


def test_tushunmadim_guruhsiz_ham_ishlaydi():
    assert "Tushunmadim" in texts.tushunmadim("", [])


def test_ai_ulanmadi_vazifa_komandasini_taklif_qiladi():
    """AI ishlamasa, foydalanuvchi nima qilishini bilishi kerak."""
    assert "/vazifa" in texts.AI_ULANMADI


def test_kunlar_matni():
    assert texts.kunlar_matni([1, 2, 3, 4, 5, 6, 7]) == "har kuni"
    assert texts.kunlar_matni([]) == "har kuni"
    assert texts.kunlar_matni([1, 2, 3, 4, 5, 6]) == "ish kunlari (Du–Sh)"
    assert texts.kunlar_matni([1, 3]) == "Du, Ch"


def test_tasdiq_bloki_doimiy_va_bir_martalik():
    doimiy = texts.tasdiq_bloki("Qurilish", "doimiy", "", [1, 2, 3, 4, 5, 6], ["tekshiruv"])
    assert "🔁" in doimiy and "ish kunlari" in doimiy

    bir = texts.tasdiq_bloki("Qurilish", "bir_martalik", "2026-03-11", [], ["suvash"])
    assert "📌" in bir and "2026-03-11" in bir
