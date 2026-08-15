"""
task_parser.py — admin yozgan erkin matndan vazifalarni ajratib olish.

Admin shaxsiy chatda oddiy gap bilan yozadi, masalan:

    "Qurilish guruhiga ertaga: devor suvash, elektr chizmasini tugatish.
     Ta'mirlash guruhiga har kuni xavfsizlik tekshiruvi."

Bu qatlam matnni Claude'ga yuboradi va qaysi guruhga, qaysi kunga, qanday
vazifa berilayotganini JSON ko'rinishida qaytaradi.

MUHIM: bu qatlam ham kritik yo'l EMAS. AI ishlamasa None qaytadi va admin
eski `/vazifa` komandasidan foydalanaveradi. Model noto'g'ri tushunishi
mumkin bo'lgani uchun natija admindan tasdiq so'ralmasdan saqlanmaydi.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

import anthropic
from anthropic import AsyncAnthropic

from services.ai_checker import MODEL, _extract_json

logger = logging.getLogger(__name__)

# Hafta kunlari nomlari (ISO: 1 = dushanba)
HAFTA_KUNLARI = {
    1: "dushanba", 2: "seshanba", 3: "chorshanba", 4: "payshanba",
    5: "juma", 6: "shanba", 7: "yakshanba",
}


def _system_prompt(guruhlar_matni: str, bugun: str, ertaga: str, bugun_kuni: str) -> str:
    return (
        "Sen ish vazifalarini taqsimlovchi yordamchisan. Foydalanuvchi o'zbek "
        "tilida erkin gap bilan yozadi, sen undan qaysi guruhga, qaysi kunga, "
        "qanday vazifa berilayotganini ajratib olasan.\n\n"
        f"Mavjud guruhlar:\n{guruhlar_matni}\n\n"
        f"Bugun: {bugun} ({bugun_kuni})\n"
        f"Ertaga: {ertaga}\n\n"
        "Qoidalar:\n"
        "- Guruhni topishda KENG fikrla. Foydalanuvchi guruh nomini to'liq "
        "yozmaydi: qisqartiradi, xato yozadi, boshqa so'z bilan ataydi "
        "('jamoa', 'brigada', 'kanal', 'bo'lim' deyishi mumkin). Nomning "
        "bir qismi mos kelsa ham o'sha guruhni tanla. Masalan 'disney "
        "jamoasi' -> nomida 'Disney' bor guruh.\n"
        "- Guruh umuman aytilmagan bo'lsa-yu, ro'yxatda FAQAT BITTA guruh "
        "bo'lsa — o'shani tanla.\n"
        "- Vazifa buyruq shaklida bo'lishi mumkin ('tozalikni tekshir', "
        "'ishchilar tozalikni tekshirsin') — bu ham vazifa, uni qabul qil.\n"
        "- 'hozir' yoki 'bugun' deyilsa sana bugun bo'ladi.\n"
        "- tushunarli=false ni FAQAT haqiqatan iloji bo'lmaganda qaytar: "
        "bir necha guruh teng darajada mos kelsa yoki matnda umuman vazifa "
        "bo'lmasa. Bunda savol maydoniga o'zbekcha aniq savol yoz va "
        "mumkin bo'lgan guruh nomlarini sanab o't.\n"
        "- 'har kuni', 'doimiy', 'har safar' kabi so'zlar bo'lsa tur='doimiy'. "
        "Aks holda tur='bir_martalik'.\n"
        "- 'ish kunlari' = hafta_kunlari [1,2,3,4,5,6] (yakshanba dam olish).\n"
        "- 'har kuni' = hafta_kunlari [1,2,3,4,5,6,7].\n"
        "- Bir_martalik uchun sana YYYY-MM-DD. Sana aytilmasa bugunni yoz.\n"
        "- Har bir vazifani alohida qatorga ajrat, qisqa va aniq yoz.\n"
        "- Bir xabarda bir necha guruh bo'lishi mumkin — har biri alohida "
        "topshiriq bo'ladi.\n\n"
        "NIYATNI ANIQLASH (birinchi qadam):\n"
        "- Foydalanuvchi ish TOPSHIRAYOTGAN bo'lsa (kimdir nimadir qilsin) "
        "-> niyat='vazifa'.\n"
        "- Foydalanuvchi ma'lumot SO'RAYOTGAN bo'lsa (kim, nima, qachon, "
        "qancha, qaysi, nega; '...bermadi?', '...bormi?', 'ko'rsat', 'ayt') "
        "-> niyat='savol'. Bunda topshiriqlar bo'sh ro'yxat bo'ladi.\n\n"
        "FAQAT quyidagi JSON obyektini qaytar. Izoh, markdown yoki backtick "
        "qo'shma:\n"
        "{\n"
        '  "niyat": "vazifa",\n'
        '  "tushunarli": true,\n'
        '  "savol": "",\n'
        '  "topshiriqlar": [\n'
        "    {\n"
        '      "guruh_id": 1,\n'
        '      "tur": "bir_martalik",\n'
        '      "sana": "2026-08-16",\n'
        '      "hafta_kunlari": [],\n'
        '      "vazifalar": ["devor suvash", "elektr chizmasini tugatish"]\n'
        "    }\n"
        "  ]\n"
        "}"
    )


def _normalize(
    data: dict[str, Any],
    ruxsat_etilgan_guruhlar: set[int],
    bugun: str,
) -> dict[str, Any]:
    """AI natijasini xavfsiz, kutilgan turlarga keltiradi."""
    topshiriqlar: list[dict[str, Any]] = []

    xom = data.get("topshiriqlar")
    if not isinstance(xom, list):
        xom = []

    for t in xom:
        if not isinstance(t, dict):
            continue
        try:
            guruh_id = int(t.get("guruh_id"))
        except (TypeError, ValueError):
            continue
        # Mavjud bo'lmagan guruhga vazifa yozib qo'ymaymiz
        if guruh_id not in ruxsat_etilgan_guruhlar:
            continue

        vazifalar = t.get("vazifalar")
        if not isinstance(vazifalar, list):
            continue
        vazifalar = [str(v).strip() for v in vazifalar if str(v).strip()]
        if not vazifalar:
            continue

        tur = "doimiy" if str(t.get("tur", "")).strip() == "doimiy" else "bir_martalik"

        kunlar_xom = t.get("hafta_kunlari")
        kunlar: list[int] = []
        if isinstance(kunlar_xom, list):
            for k in kunlar_xom:
                try:
                    n = int(k)
                except (TypeError, ValueError):
                    continue
                if 1 <= n <= 7:
                    kunlar.append(n)
        kunlar = sorted(set(kunlar))
        if tur == "doimiy" and not kunlar:
            kunlar = [1, 2, 3, 4, 5, 6, 7]

        sana = str(t.get("sana", "") or "").strip()
        try:
            datetime.strptime(sana, "%Y-%m-%d")
        except ValueError:
            sana = bugun

        topshiriqlar.append({
            "guruh_id": guruh_id,
            "tur": tur,
            "sana": sana,
            "hafta_kunlari": kunlar,
            "vazifalar": vazifalar,
        })

    savol = str(data.get("savol", "") or "").strip()
    niyat = "savol" if str(data.get("niyat", "")).strip() == "savol" else "vazifa"

    # Vazifa niyatida topshiriq chiqmagan bo'lsa — bu tushunarsiz xabar.
    # Savol niyatida topshiriq bo'lmasligi normal.
    tushunarli = (
        niyat == "savol"
        or (bool(data.get("tushunarli", False)) and bool(topshiriqlar))
    )

    return {
        "niyat": niyat,
        "tushunarli": tushunarli,
        "savol": savol,
        "topshiriqlar": topshiriqlar,
    }


class TaskParser:
    """Erkin matndan vazifalarni ajratib oluvchi xizmat."""

    def __init__(self, api_key: str) -> None:
        self.client: Optional[AsyncAnthropic] = (
            AsyncAnthropic(api_key=api_key) if api_key else None
        )

    @property
    def enabled(self) -> bool:
        """Erkin matn bilan vazifa berish yoqilganmi."""
        return self.client is not None

    async def parse(
        self,
        text: str,
        groups: list[dict[str, Any]],
        tz: ZoneInfo,
    ) -> Optional[dict[str, Any]]:
        """
        Matnni tahlil qilib normallashtirilgan natijani qaytaradi.
        Har qanday xato holatda None qaytaradi.
        """
        if self.client is None or not groups:
            return None

        guruhlar_matni = "\n".join(
            f"- id={int(g['id'])}, nomi: {g.get('name') or 'nomsiz'}" for g in groups
        )
        hozir = datetime.now(tz)
        bugun = hozir.strftime("%Y-%m-%d")
        ertaga = (hozir + timedelta(days=1)).strftime("%Y-%m-%d")
        bugun_kuni = HAFTA_KUNLARI[hozir.isoweekday()]

        try:
            response = await self.client.messages.create(
                model=MODEL,
                max_tokens=1500,
                system=_system_prompt(guruhlar_matni, bugun, ertaga, bugun_kuni),
                thinking={"type": "disabled"},
                output_config={"effort": "low"},
                messages=[{"role": "user", "content": text}],
            )
        except anthropic.APITimeoutError:
            logger.error("Vazifa tahlili: API timeout")
            return None
        except anthropic.RateLimitError:
            logger.error("Vazifa tahlili: rate limit (429)")
            return None
        except anthropic.APIConnectionError:
            logger.error("Vazifa tahlili: ulanish xatosi")
            return None
        except anthropic.APIStatusError as e:
            logger.error("Vazifa tahlili: API xatosi (status %s)", e.status_code)
            return None
        except Exception:
            logger.error("Vazifa tahlili: kutilmagan xato", exc_info=True)
            return None

        javob = "".join(b.text for b in response.content if b.type == "text")
        data = _extract_json(javob)
        if data is None:
            logger.error("Vazifa tahlili: JSON parse qilib bo'lmadi: %r", javob[:200])
            return None

        return _normalize(data, {int(g["id"]) for g in groups}, bugun)
