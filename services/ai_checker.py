"""
ai_checker.py — Claude API orqali hisobotni baholash.

Guruhdan kelgan hisobot matni + shu guruhning bugungi vazifalari Claude'ga
yuboriladi. Model faqat JSON qaytaradi (izohsiz, markdownsiz).

MUHIM: bu qatlam kritik yo'l EMAS. API timeout, rate limit yoki JSON parse
xatosi bo'lsa — funksiya None qaytaradi, chaqiruvchi hisobotni 'pending'
holatida qoldiradi va bot ishlashda davom etadi.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import anthropic
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

# Foydalanuvchi spetsifikatsiyasida ko'rsatilgan model
MODEL = "claude-sonnet-4-6"

# Baholash mezonlari va qat'iy JSON formati tushuntirilgan system prompt
SYSTEM_PROMPT = (
    "Sen ish hisobotlarini baholovchi yordamchisan. Sizga o'zbek tilidagi "
    "ish hisoboti va (agar bo'lsa) shu kunning vazifalari beriladi.\n\n"
    "Hisobot 4 qismdan iborat bo'lishi kutiladi:\n"
    "1) Bajarilgan ishlar\n"
    "2) Bajarilmagani va sababi\n"
    "3) Muammolar / kerak bo'lgan yordam\n"
    "4) Ertangi reja\n\n"
    "Baholash mezonlari:\n"
    "- 4 ta bo'lim ham to'ldirilganmi;\n"
    "- Javob aniq faktlar bilanmi yoki umumiy gapmi "
    "(masalan 'hammasi yaxshi', 'ishladik' — bu umumiy gap);\n"
    "- Bugungi vazifalar bilan mos keladimi;\n"
    "- baho: 1 = bo'sh yoki formal, 5 = to'liq va aniq.\n\n"
    "FAQAT quyidagi JSON obyektini qaytar. Hech qanday izoh, markdown, "
    "backtick yoki qo'shimcha matn qo'shma:\n"
    "{\n"
    '  "toliq": true,\n'
    '  "yetishmagan": ["ertangi reja"],\n'
    '  "muammo_bormi": false,\n'
    '  "muammo_qisqacha": "",\n'
    '  "baho": 4,\n'
    '  "qisqa_xulosa": "3 ta obyekt yakunlandi, 1 tasi kechikdi"\n'
    "}\n\n"
    "Qoidalar:\n"
    "- toliq: 4 bo'lim ham mazmunli to'ldirilgan bo'lsa true;\n"
    "- yetishmagan: to'ldirilmagan yoki yetarli bo'lmagan bo'limlar nomlari ro'yxati;\n"
    "- muammo_bormi: hisobotda hal qilinishi kerak bo'lgan jiddiy muammo/to'siq bo'lsa true;\n"
    "- muammo_qisqacha: muammo qisqacha (muammo bo'lmasa bo'sh matn);\n"
    "- baho: 1 dan 5 gacha butun son;\n"
    "- qisqa_xulosa: hisobotning bir jumlalik xulosasi."
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
    }


class AiChecker:
    """Claude API bilan hisobotni baholaydigan xizmat."""

    def __init__(self, api_key: str) -> None:
        # Kalit bo'lmasa mijoz None bo'ladi — AI qatlamini o'chirib qo'yadi
        self.client: Optional[AsyncAnthropic] = (
            AsyncAnthropic(api_key=api_key) if api_key else None
        )
        if self.client is None:
            logger.warning("ANTHROPIC_API_KEY yo'q — AI tekshiruv o'chirilgan.")

    @property
    def enabled(self) -> bool:
        """AI tekshiruv yoqilganmi (kalit mavjudmi)."""
        return self.client is not None

    async def check_report(
        self,
        report_text: str,
        tasks: list[str],
    ) -> Optional[dict[str, Any]]:
        """
        Hisobotni baholaydi va normallashtirilgan natija dict'ini qaytaradi.
        Har qanday xato holatda None qaytaradi (bot ishlashda davom etadi).
        """
        if self.client is None:
            return None

        tasks_text = (
            "\n".join(f"- {t}" for t in tasks)
            if tasks
            else "(bugun uchun alohida vazifa belgilanmagan)"
        )
        user_message = (
            f"Bugungi vazifalar:\n{tasks_text}\n\n"
            f"Hisobot matni:\n{report_text}"
        )

        try:
            response = await self.client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                thinking={"type": "disabled"},  # oddiy tasnif — fikrlash shart emas
                # Model standart holatda "high" darajada ishlaydi; bu vazifa uchun
                # "low" yetarli va sezilarli darajada arzon/tez.
                output_config={"effort": "low"},
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
            logger.error("AI: API xatosi (status %s)", e.status_code)
            return None
        except Exception:
            logger.error("AI: kutilmagan xato", exc_info=True)
            return None

        # Javob matnini yig'amiz
        text = "".join(
            block.text for block in response.content if block.type == "text"
        )

        data = _extract_json(text)
        if data is None:
            logger.error("AI: JSON parse qilib bo'lmadi. Javob: %r", text[:200])
            return None

        return _normalize(data)
