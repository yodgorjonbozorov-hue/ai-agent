"""
test_recurring.py — doimiy (takrorlanuvchi) vazifalar testlari.
"""

from __future__ import annotations

from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Tashkent")
DATE = "2026-03-10"        # seshanba
DUSHANBA, SESHANBA, YAKSHANBA = 1, 2, 7


async def test_doimiy_vazifa_qoshiladi(database, group_id):
    task_id = await database.add_recurring_task(
        group_id, "Xavfsizlik tekshiruvi", tz=TZ
    )
    hammasi = await database.get_recurring_tasks(group_id)
    assert len(hammasi) == 1
    assert hammasi[0]["id"] == task_id
    assert hammasi[0]["text"] == "Xavfsizlik tekshiruvi"
    # Kunlar ko'rsatilmasa — har kuni
    assert hammasi[0]["weekdays"] == "1,2,3,4,5,6,7"


async def test_hafta_kunlari_saqlanadi(database, group_id):
    await database.add_recurring_task(
        group_id, "Ish kunlari yig'ilishi", weekdays=[1, 2, 3, 4, 5, 6], tz=TZ
    )
    hammasi = await database.get_recurring_tasks(group_id)
    assert hammasi[0]["weekdays"] == "1,2,3,4,5,6"


async def test_notogri_kunlar_tozalanadi(database, group_id):
    """Model 0 yoki 9 kabi noto'g'ri kun qaytarsa ham baza buzilmasligi kerak."""
    await database.add_recurring_task(
        group_id, "Vazifa", weekdays=[0, 3, 3, 9, 5], tz=TZ
    )
    assert (await database.get_recurring_tasks(group_id))[0]["weekdays"] == "3,5"


async def test_doimiy_vazifa_ochiriladi(database, group_id):
    task_id = await database.add_recurring_task(group_id, "Vaqtinchalik", tz=TZ)
    await database.delete_recurring_task(task_id)
    assert await database.get_recurring_tasks(group_id) == []


# --------------------------------------------------------------------------
# Kunga ko'chirish
# --------------------------------------------------------------------------

async def test_doimiy_vazifa_kunga_kochiriladi(database, group_id):
    await database.add_recurring_task(group_id, "Har kungi tekshiruv", tz=TZ)

    qoshilgan = await database.apply_recurring_tasks(group_id, DATE, SESHANBA)

    assert qoshilgan == 1
    vazifalar = await database.get_tasks(group_id, DATE)
    assert [v["text"] for v in vazifalar] == ["Har kungi tekshiruv"]


async def test_notogri_kunda_kochirilmaydi(database, group_id):
    """Faqat dushanbaga mo'ljallangan vazifa seshanba kuni qo'shilmasligi kerak."""
    await database.add_recurring_task(
        group_id, "Dushanba yig'ilishi", weekdays=[DUSHANBA], tz=TZ
    )
    assert await database.apply_recurring_tasks(group_id, DATE, SESHANBA) == 0
    assert await database.get_tasks(group_id, DATE) == []


async def test_yakshanba_dam_olish(database, group_id):
    await database.add_recurring_task(
        group_id, "Ish kunlari vazifasi", weekdays=[1, 2, 3, 4, 5, 6], tz=TZ
    )
    assert await database.apply_recurring_tasks(group_id, DATE, YAKSHANBA) == 0


async def test_takroriy_kochirish_dublikat_yaratmaydi(database, group_id):
    """Bot kun davomida qayta ishga tushsa, vazifa ikki marta qo'shilmasligi kerak."""
    await database.add_recurring_task(group_id, "Har kungi tekshiruv", tz=TZ)

    birinchi = await database.apply_recurring_tasks(group_id, DATE, SESHANBA)
    ikkinchi = await database.apply_recurring_tasks(group_id, DATE, SESHANBA)

    assert birinchi == 1
    assert ikkinchi == 0
    assert len(await database.get_tasks(group_id, DATE)) == 1


async def test_qolda_qoshilgan_vazifa_saqlanib_qoladi(database, group_id):
    """Doimiy vazifalar qo'lda yozilganlarini o'chirib yubormasligi kerak."""
    await database.add_task(group_id, DATE, "Qo'lda yozilgan vazifa")
    await database.add_recurring_task(group_id, "Doimiy vazifa", tz=TZ)

    await database.apply_recurring_tasks(group_id, DATE, SESHANBA)

    matnlar = [v["text"] for v in await database.get_tasks(group_id, DATE)]
    assert "Qo'lda yozilgan vazifa" in matnlar
    assert "Doimiy vazifa" in matnlar


async def test_boshqa_guruhning_vazifasi_aralashmaydi(database, group_id):
    ikkinchi_guruh = await database.add_or_update_group(-100999, "Ikkinchi", tz=TZ)
    await database.add_recurring_task(ikkinchi_guruh, "Boshqa guruh vazifasi", tz=TZ)

    assert await database.apply_recurring_tasks(group_id, DATE, SESHANBA) == 0
    assert await database.get_tasks(group_id, DATE) == []


async def test_add_task_if_absent(database, group_id):
    assert await database.add_task_if_absent(group_id, DATE, "Vazifa") is True
    assert await database.add_task_if_absent(group_id, DATE, "Vazifa") is False
    # Boshqa sanaga o'sha matn qo'shilaveradi
    assert await database.add_task_if_absent(group_id, "2026-03-11", "Vazifa") is True
