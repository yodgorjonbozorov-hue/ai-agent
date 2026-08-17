"""
ai.py — botning "ovozi": guruhga va adminga boradigan matnlarni AI yozadi.

Ilgari bot faqat texts.py dagi tayyor shablonlarni yuborardi, AI esa
faqat hisobotni "to'liq / to'liq emas" deb baholardi. Endi aksincha:

  - hisobotga javobni AI yozadi (odam nima yozganiga qarab, jonli tilda);
  - ertalabki xabar, hisobot so'rovi va eslatmalarni ham AI yozadi;
  - guruhda botga murojaat qilinsa yoki admin oddiy savol yozsa,
    javobni ham AI beradi.

texts.py dagi shablonlar endi faqat ZAXIRA: API ishlamasa (timeout, rate
limit, kalit yo'q) bot baribir javob beradi va to'xtab qolmaydi.

MUHIM: bu qatlam kritik yo'l EMAS. Har qanday xatoda funksiyalar None
qaytaradi va chaqiruvchi shablonga qaytadi.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import anthropic
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

# Standart model. .env dagi AI_MODEL orqali o'zgartirsa bo'ladi.
DEFAULT_MODEL = "claude-opus-5"

# --------------------------------------------------------------------------
# System promptlar
# --------------------------------------------------------------------------

# Bot kim va qanday gapiradi — barcha so'rovlarda umumiy qism.
_ROLE = (
    "Sen — Disney Navoiy kompaniyasining Telegram ish yordamchisisan. "
    "Xodimlar guruhlarida kunlik ish hisobotlarini yig'asan, eslatib turasan "
    "va admin bilan ishlaysan."
)

_STYLE = (
    "Qanday yozasan:\n"
    "- Faqat o'zbek tilida (lotin alifbosi), jonli va tabiiy — odam yozgandek;\n"
    "- Qisqa: odatda 1-3 jumla. Guruhda uzun matnni hech kim o'qimaydi;\n"
    "- Shablon emas. Har safar boshqacha yoz: odam aynan nima yozgan bo'lsa, "
    "shunga javob ber, uning ishini nomma-nom tilga ol. "
    "\"Hisobot qabul qilindi, rahmat\" kabi quruq, takrorlanadigan javob yozma;\n"
    "- Hurmatli va iliq, lekin ortiqcha maqtovsiz; kerak bo'lganda aniq va qat'iy;\n"
    "- Emoji ko'pi bilan bitta, ko'pincha umuman kerak emas;\n"
    "- Markdown, sarlavha va yulduzcha ishlatma — oddiy matn yoz;\n"
    "- Faktlarni o'ylab topma: faqat senga berilgan ma'lumotga tayan. "
    "Bilmasang, bilmasligingni ayt."
)

# Erkin matn yozish uchun (javobda faqat yuboriladigan xabar bo'lishi kerak)
WRITER_SYSTEM = (
    f"{_ROLE}\n\n{_STYLE}\n\n"
    "Javobingda faqat Telegramga yuboriladigan matnning o'zi bo'lsin — "
    "izoh, sarlavha, tirnoq yoki \"mana matn:\" kabi kirish so'zlarisiz."
)

# Hisobotni baholash + javob yozish (natija — JSON)
REVIEW_SYSTEM = (
    f"{_ROLE}\n\n"
    "Senga xodim yuborgan ish hisoboti va (agar bo'lsa) shu kunning "
    "vazifalari beriladi. Ikkita ish qilasan: hisobotni baholaysan va "
    "guruhga yuboriladigan javob matnini o'zing yozasan.\n\n"
    "Hisobot 4 qismdan iborat bo'lishi kutiladi:\n"
    "1) Bajarilgan ishlar\n"
    "2) Bajarilmagani va sababi\n"
    "3) Muammolar / kerak bo'lgan yordam\n"
    "4) Ertangi reja\n\n"
    "Baholash mezonlari:\n"
    "- 4 ta bo'lim ham mazmunli to'ldirilganmi;\n"
    "- Javob aniq faktlar bilanmi yoki umumiy gapmi "
    "(masalan 'hammasi yaxshi', 'ishladik' — bu umumiy gap);\n"
    "- Bugungi vazifalar bilan mos keladimi;\n"
    "- baho: 1 = bo'sh yoki formal, 5 = to'liq va aniq.\n\n"
    f"{_STYLE}\n\n"
    "\"javob\" maydoniga guruhga yuboriladigan matnni yoz:\n"
    "- hisobotdagi aniq ishga ishora qil (raqam, obyekt nomi, bajarilgan ish);\n"
    "- to'ldirilmagan bo'lim bo'lsa, aynan nimani yozib yuborishni so'ra;\n"
    "- muammo aytilgan bo'lsa, uni ko'rganingni bildir va admin xabardor "
    "qilinganini ayt;\n"
    "- hisobotni yuborgan odamga murojaat qilishing mumkin.\n\n"
    "FAQAT quyidagi JSON obyektini qaytar. Hech qanday izoh, markdown yoki "
    "backtick qo'shma:\n"
    "{\n"
    '  "toliq": true,\n'
    '  "yetishmagan": ["ertangi reja"],\n'
    '  "muammo_bormi": false,\n'
    '  "muammo_qisqacha": "",\n'
    '  "baho": 4,\n'
    '  "qisqa_xulosa": "3 ta obyekt yakunlandi, 1 tasi kechikdi",\n'
    '  "javob": "Guruhga yuboriladigan tabiiy javob matni"\n'
    "}\n\n"
    "Qoidalar:\n"
    "- toliq: 4 bo'lim ham mazmunli to'ldirilgan bo'lsa true;\n"
    "- yetishmagan: to'ldirilmagan yoki yetarli bo'lmagan bo'limlar ro'yxati;\n"
    "- muammo_bormi: hal qilinishi kerak bo'lgan jiddiy muammo/to'siq bo'lsa true;\n"
    "- muammo_qisqacha: muammo qisqacha (muammo bo'lmasa bo'sh matn);\n"
    "- baho: 1 dan 5 gacha butun son;\n"
    "- qisqa_xulosa: adminning kunlik xulosasi uchun bir jumlalik xulosa;\n"
    "- javob: guruhga yuboriladigan matn (shablon emas, 1-3 jumla)."
)


def _extract_json(text: str) -> Optional[dict[str, Any]]:
    """
    Model javobidan JSON obyektini ajratib oladi.
    Model xato qilib backtick yoki matn qo'shsa ham qutqarishga urinadi.
    """
    text = text.strip()
    # Ehtiyot chorasi: ```json ... ``` bloklarini olib tashlash
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Matn ichidan birinchi { ... } blokini topishga urinamiz
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None


def _normalize(data: dict[str, Any]) -> dict[str, Any]:
    """AI natijasini xavfsiz, kutilgan turlarga keltiradi."""
    yetishmagan = data.get("yetishmagan", [])
    if not isinstance(yetishmagan, list):
        yetishmagan = []
    yetishmagan = [str(x) for x in yetishmagan]

    try:
        baho = int(data.get("baho", 3))
    except (TypeError, ValueError):
        baho = 3
    baho = max(1, min(5, baho))  # 1..5 oralig'ida ushlab turamiz

    return {
        "toliq": bool(data.get("toliq", False)),
        "yetishmagan": yetishmagan,
        "muammo_bormi": bool(data.get("muammo_bormi", False)),
        "muammo_qisqacha": str(data.get("muammo_qisqacha", "") or ""),
        "baho": baho,
        "qisqa_xulosa": str(data.get("qisqa_xulosa", "") or ""),
        "javob": str(data.get("javob", "") or "").strip(),
    }


class AiAssistant:
    """Claude API bilan matn yozadigan va hisobot baholaydigan xizmat."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        # Kalit bo'lmasa mijoz None bo'ladi — AI qatlami o'chadi, bot shablonga qaytadi
        self.model = model or DEFAULT_MODEL
        self.client: Optional[AsyncAnthropic] = (
            AsyncAnthropic(api_key=api_key) if api_key else None
        )
        if self.client is None:
            logger.warning(
                "ANTHROPIC_API_KEY yo'q — AI o'chirilgan, bot zaxira shablonlar bilan ishlaydi."
            )
        else:
            logger.info("AI yoqilgan, model: %s", self.model)

    @property
    def enabled(self) -> bool:
        """AI yoqilganmi (kalit mavjudmi)."""
        return self.client is not None

    # ------------------------------------------------------------------
    # Past darajali so'rov
    # ------------------------------------------------------------------

    async def _ask(
        self,
        system: str,
        user_message: str,
        max_tokens: int = 800,
        effort: str = "low",
    ) -> Optional[str]:
        """
        Claude'ga bitta so'rov yuboradi va matnli javobni qaytaradi.
        Har qanday xatoda None (chaqiruvchi zaxira matnga o'tadi).
        """
        if self.client is None:
            return None

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                thinking={"type": "adaptive"},
                output_config={"effort": effort},
                messages=[{"role": "user", "content": user_message}],
            )
        except anthropic.APITimeoutError:
            logger.error("AI: API timeout")
            return None
        except anthropic.RateLimitError:
            logger.error("AI: rate limit (429)")
            return None
        except anthropic.APIConnectionError:
            logger.error("AI: ulanish xatosi")
            return None
        except anthropic.APIStatusError as e:
            logger.error("AI: API xatosi (status %s): %s", e.status_code, e.message)
            return None
        except Exception:
            logger.error("AI: kutilmagan xato", exc_info=True)
            return None

        if response.stop_reason == "refusal":
            logger.error("AI: so'rov rad etildi (refusal)")
            return None

        text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

        return text or None

    # ------------------------------------------------------------------
    # Erkin matn yozish
    # ------------------------------------------------------------------

    async def compose(
        self,
        task: str,
        context: str = "",
        max_tokens: int = 600,
    ) -> Optional[str]:
        """
        Berilgan vazifa bo'yicha yuboriladigan xabar matnini yozadi.

        task    — nima yozish kerakligi ("guruhga ertalabki xabar yoz ...");
        context — foydalanish mumkin bo'lgan faktlar (vazifalar, guruh nomi ...).
        """
        parts = [task]
        if context.strip():
            parts.append(f"Ma'lumot:\n{context.strip()}")
        return await self._ask(WRITER_SYSTEM, "\n\n".join(parts), max_tokens=max_tokens)

    async def answer(
        self,
        question: str,
        context: str = "",
        max_tokens: int = 700,
    ) -> Optional[str]:
        """
        Odamning savoliga/xabariga javob yozadi (guruhda yoki admin chatida).
        Kontekstda bo'lmagan narsani o'ylab topmasligi so'raladi.
        """
        parts = [
            "Quyidagi xabarga javob yoz. Kontekstda bo'lmagan ma'lumotni "
            "o'ylab topma — bilmasang, buni ochiq ayt.",
        ]
        if context.strip():
            parts.append(f"Kontekst:\n{context.strip()}")
        parts.append(f"Xabar:\n{question.strip()}")
        return await self._ask(WRITER_SYSTEM, "\n\n".join(parts), max_tokens=max_tokens)

    # ------------------------------------------------------------------
    # Hisobotni baholash + javob matni
    # ------------------------------------------------------------------

    async def check_report(
        self,
        report_text: str,
        tasks: list[str],
        group_name: str = "",
        author: str = "",
    ) -> Optional[dict[str, Any]]:
        """
        Hisobotni baholaydi va guruhga yuboriladigan javob matnini yozadi.
        Natija — normallashtirilgan dict (ichida "javob" bor) yoki None.
        """
        if self.client is None:
            return None

        tasks_text = (
            "\n".join(f"- {t}" for t in tasks)
            if tasks
            else "(bugun uchun alohida vazifa belgilanmagan)"
        )
        author_name = author or "noma'lum"
        user_message = (
            f"Guruh: {group_name or 'nomsiz'}\n"
            f"Hisobotni yuborgan: {author_name}\n\n"
            f"Bugungi vazifalar:\n{tasks_text}\n\n"
            f"Hisobot matni:\n{report_text}"
        )

        text = await self._ask(
            REVIEW_SYSTEM, user_message, max_tokens=1200, effort="medium"
        )
        if text is None:
            return None

        data = _extract_json(text)
        if data is None:
            logger.error("AI: JSON parse qilib bo'lmadi. Javob: %r", text[:200])
            return None

        return _normalize(data)
