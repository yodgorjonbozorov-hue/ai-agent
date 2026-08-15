"""
test_ai_checker.py — AI javobini ajratish va normallashtirish testlari.

Bu yerda haqiqiy API chaqirilmaydi: faqat model javobini o'qish mantig'i
tekshiriladi. AI qatlami kritik yo'l emas, shuning uchun har qanday buzuq
javobda ham funksiyalar yiqilmasligi kerak.
"""

from __future__ import annotations

from services.ai_checker import AiChecker, _extract_json, _normalize


# --------------------------------------------------------------------------
# JSON ajratish
# --------------------------------------------------------------------------

def test_toza_json_oqiladi():
    assert _extract_json('{"toliq": true, "baho": 5}') == {"toliq": True, "baho": 5}


def test_markdown_blokdan_json_ajratiladi():
    javob = '```json\n{"toliq": false, "baho": 2}\n```'
    assert _extract_json(javob) == {"toliq": False, "baho": 2}


def test_matn_orasidagi_json_topiladi():
    javob = 'Mana natija:\n{"toliq": true, "baho": 4}\nUmid qilamanki foydali.'
    assert _extract_json(javob) == {"toliq": True, "baho": 4}


def test_json_bolmasa_none_qaytadi():
    assert _extract_json("Kechirasiz, javob bera olmayman.") is None
    assert _extract_json("") is None


def test_buzuq_json_none_qaytadi():
    assert _extract_json('{"toliq": true, "baho":}') is None


# --------------------------------------------------------------------------
# Normallashtirish — model noto'g'ri tur qaytarsa ham yiqilmaslik kerak
# --------------------------------------------------------------------------

def test_toliq_natija_ozgarishsiz_qoladi():
    natija = _normalize({
        "toliq": True,
        "yetishmagan": [],
        "muammo_bormi": False,
        "muammo_qisqacha": "",
        "baho": 5,
        "qisqa_xulosa": "Hammasi bajarildi",
    })
    assert natija["toliq"] is True
    assert natija["baho"] == 5
    assert natija["qisqa_xulosa"] == "Hammasi bajarildi"


def test_bosh_dict_xavfsiz_standartlarga_tushadi():
    natija = _normalize({})
    assert natija == {
        "toliq": False,
        "yetishmagan": [],
        "muammo_bormi": False,
        "muammo_qisqacha": "",
        "baho": 3,
        "qisqa_xulosa": "",
    }


def test_baho_1_5_oraligida_ushlanadi():
    assert _normalize({"baho": 99})["baho"] == 5
    assert _normalize({"baho": -4})["baho"] == 1
    assert _normalize({"baho": "yaxshi"})["baho"] == 3
    assert _normalize({"baho": None})["baho"] == 3


def test_yetishmagan_royxat_bolmasa_boshatiladi():
    assert _normalize({"yetishmagan": "ertangi reja"})["yetishmagan"] == []
    assert _normalize({"yetishmagan": [1, 2]})["yetishmagan"] == ["1", "2"]


def test_null_matnlar_bosh_satrga_aylanadi():
    natija = _normalize({"muammo_qisqacha": None, "qisqa_xulosa": None})
    assert natija["muammo_qisqacha"] == ""
    assert natija["qisqa_xulosa"] == ""


# --------------------------------------------------------------------------
# Kalitsiz ishlash — AI o'chirilgan holat
# --------------------------------------------------------------------------

def test_kalitsiz_ai_ochiriladi():
    checker = AiChecker(api_key="")
    assert checker.enabled is False
    assert checker.client is None


async def test_kalitsiz_tekshiruv_none_qaytaradi():
    """Kalit bo'lmasa bot yiqilmaydi — hisobot 'pending' holatida qoladi."""
    checker = AiChecker(api_key="")
    assert await checker.check_report("Uzun hisobot matni", ["vazifa"]) is None
