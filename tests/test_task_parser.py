"""
test_task_parser.py — erkin matndan ajratilgan vazifalarni normallashtirish.

Haqiqiy API chaqirilmaydi. Model noto'g'ri yoki xavfli qiymat qaytarsa ham
bot yiqilmasligi va begona guruhga vazifa yozmasligi tekshiriladi.
"""

from __future__ import annotations

from services.task_parser import TaskParser, _normalize

GURUHLAR = {1, 2}
BUGUN = "2026-03-10"


def _bitta(natija):
    assert len(natija["topshiriqlar"]) == 1
    return natija["topshiriqlar"][0]


def test_oddiy_bir_martalik_topshiriq():
    natija = _normalize({
        "tushunarli": True,
        "topshiriqlar": [{
            "guruh_id": 1, "tur": "bir_martalik", "sana": "2026-03-11",
            "hafta_kunlari": [], "vazifalar": ["devor suvash", "pol tayyorlash"],
        }],
    }, GURUHLAR, BUGUN)

    assert natija["tushunarli"] is True
    t = _bitta(natija)
    assert t["guruh_id"] == 1
    assert t["tur"] == "bir_martalik"
    assert t["sana"] == "2026-03-11"
    assert t["vazifalar"] == ["devor suvash", "pol tayyorlash"]


def test_doimiy_topshiriq_kunlari():
    t = _bitta(_normalize({
        "tushunarli": True,
        "topshiriqlar": [{
            "guruh_id": 2, "tur": "doimiy", "hafta_kunlari": [1, 2, 3, 4, 5, 6],
            "vazifalar": ["xavfsizlik tekshiruvi"],
        }],
    }, GURUHLAR, BUGUN))

    assert t["tur"] == "doimiy"
    assert t["hafta_kunlari"] == [1, 2, 3, 4, 5, 6]


def test_doimiy_kunsiz_har_kunga_aylanadi():
    t = _bitta(_normalize({
        "tushunarli": True,
        "topshiriqlar": [{
            "guruh_id": 1, "tur": "doimiy", "vazifalar": ["tekshiruv"],
        }],
    }, GURUHLAR, BUGUN))
    assert t["hafta_kunlari"] == [1, 2, 3, 4, 5, 6, 7]


def test_begona_guruhga_vazifa_yozilmaydi():
    """Model mavjud bo'lmagan guruh id qaytarsa, u tashlab yuboriladi."""
    natija = _normalize({
        "tushunarli": True,
        "topshiriqlar": [{
            "guruh_id": 999, "tur": "bir_martalik", "sana": BUGUN,
            "vazifalar": ["vazifa"],
        }],
    }, GURUHLAR, BUGUN)

    assert natija["topshiriqlar"] == []
    assert natija["tushunarli"] is False


def test_notogri_sana_bugunga_tushadi():
    t = _bitta(_normalize({
        "tushunarli": True,
        "topshiriqlar": [{
            "guruh_id": 1, "tur": "bir_martalik", "sana": "ertaga",
            "vazifalar": ["vazifa"],
        }],
    }, GURUHLAR, BUGUN))
    assert t["sana"] == BUGUN


def test_notogri_hafta_kunlari_tozalanadi():
    t = _bitta(_normalize({
        "tushunarli": True,
        "topshiriqlar": [{
            "guruh_id": 1, "tur": "doimiy",
            "hafta_kunlari": [0, 3, "5", 9, None], "vazifalar": ["vazifa"],
        }],
    }, GURUHLAR, BUGUN))
    assert t["hafta_kunlari"] == [3, 5]


def test_bosh_vazifalar_tashlab_yuboriladi():
    natija = _normalize({
        "tushunarli": True,
        "topshiriqlar": [{
            "guruh_id": 1, "tur": "bir_martalik", "sana": BUGUN,
            "vazifalar": ["   ", ""],
        }],
    }, GURUHLAR, BUGUN)
    assert natija["topshiriqlar"] == []


def test_bir_nechta_guruh():
    natija = _normalize({
        "tushunarli": True,
        "topshiriqlar": [
            {"guruh_id": 1, "tur": "bir_martalik", "sana": BUGUN,
             "vazifalar": ["birinchi"]},
            {"guruh_id": 2, "tur": "doimiy", "hafta_kunlari": [1],
             "vazifalar": ["ikkinchi"]},
        ],
    }, GURUHLAR, BUGUN)
    assert len(natija["topshiriqlar"]) == 2


def test_tushunarsiz_xabar_savol_bilan():
    natija = _normalize({
        "tushunarli": False,
        "savol": "Qaysi guruhga?",
        "topshiriqlar": [],
    }, GURUHLAR, BUGUN)
    assert natija["tushunarli"] is False
    assert natija["savol"] == "Qaysi guruhga?"


def test_bosh_javob_yiqilmaydi():
    natija = _normalize({}, GURUHLAR, BUGUN)
    assert natija == {
        "niyat": "vazifa", "tushunarli": False, "savol": "", "topshiriqlar": [],
    }


# --------------------------------------------------------------------------
# Niyat: vazifa berish yoki savol
# --------------------------------------------------------------------------

def test_savol_niyati_topshiriqsiz_ham_tushunarli():
    """Savolda topshiriq bo'lmasligi normal — 'tushunmadim' chiqmasligi kerak."""
    natija = _normalize(
        {"niyat": "savol", "topshiriqlar": []}, GURUHLAR, BUGUN
    )
    assert natija["niyat"] == "savol"
    assert natija["tushunarli"] is True


def test_vazifa_niyatida_topshiriqsiz_tushunarsiz():
    natija = _normalize(
        {"niyat": "vazifa", "tushunarli": True, "topshiriqlar": []},
        GURUHLAR, BUGUN,
    )
    assert natija["tushunarli"] is False


def test_notanish_niyat_vazifa_deb_qabul_qilinadi():
    natija = _normalize(
        {"niyat": "allaqanday", "tushunarli": True,
         "topshiriqlar": [{"guruh_id": 1, "tur": "bir_martalik",
                           "sana": BUGUN, "vazifalar": ["ish"]}]},
        GURUHLAR, BUGUN,
    )
    assert natija["niyat"] == "vazifa"


def test_buzuq_turlar_yiqilmaydi():
    natija = _normalize({
        "tushunarli": True,
        "topshiriqlar": "bu ro'yxat emas",
    }, GURUHLAR, BUGUN)
    assert natija["topshiriqlar"] == []


def test_kalitsiz_parser_ochirilgan():
    parser = TaskParser(api_key="")
    assert parser.enabled is False


async def test_kalitsiz_parse_none_qaytaradi():
    parser = TaskParser(api_key="")
    natija = await parser.parse("Qurilish guruhiga vazifa", [{"id": 1}], None)
    assert natija is None
