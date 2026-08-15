"""
assistant.py — admin savollariga javob berish.

Admin komandalarni eslab qolmasdan, oddiy gap bilan so'rashi mumkin:

    "Kim bugun hisobot bermadi?"
    "Disney guruhi kecha nima yozdi?"
    "Bu hafta qaysi guruh eng yomon ishlayapti?"

Ishlash tartibi: avval bazadan qisqa "holat lavhasi" yig'iladi, so'ng u
savol bilan birga Claude'ga beriladi. Model FAQAT shu lavhadagi ma'lumotga
tayanadi — o'ylab topmasligi uchun bu system promptda qat'iy aytilgan.

MUHIM: bu qatlam ham kritik yo'l EMAS — xato bo'lsa None qaytadi.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import anthropic
from anthropic import AsyncAnthropic

from services.ai_checker import MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Sen ish hisobotlarini kuzatuvchi botning yordamchisisan. Rahbar "
    "(admin) senga savol beradi, sen quyida berilgan HOLAT MA'LUMOTIGA "
    "tayanib javob berasan.\n\n"
    "Qoidalar:\n"
    "- FAQAT berilgan ma'lumotdan foydalanan. Hech narsani o'ylab topma.\n"
    "- Ma'lumotda javob yo'q bo'lsa, ochiq ayt: 'Bu haqda ma'lumotim yo'q' "
    "va nima yetishmayotganini tushuntir.\n"
    "- O'zbek tilida (lotin), qisqa va aniq javob ber.\n"
    "- Raqamlar va guruh nomlarini aynan ma'lumotdagidek yoz.\n"
    "- Javobni to'g'ridan-to'g'ri boshla. 'Ma'lumotga ko'ra' kabi "
    "kirish so'zlar shart emas.\n"
    "- Ro'yxat kerak bo'lsa qisqa qatorlar bilan yoz, jadval tuzma."
)


class Assistant:
    """Admin savollariga baza ma'lumoti asosida javob beradi."""

    def __init__(self, api_key: str) -> None:
        self.client: Optional[AsyncAnthropic] = (
            AsyncAnthropic(api_key=api_key) if api_key else None
        )

    @property
    def enabled(self) -> bool:
        return self.client is not None

    async def answer(self, question: str, context: str) -> Optional[str]:
        """
        Savolga javob matnini qaytaradi.
        Har qanday xato holatda None qaytaradi.
        """
        if self.client is None:
            return None

        user_message = (
            f"HOLAT MA'LUMOTI:\n{context}\n\n"
            f"RAHBARNING SAVOLI:\n{question}"
        )

        try:
            response = await self.client.messages.create(
                model=MODEL,
                max_tokens=1200,
                system=SYSTEM_PROMPT,
                thinking={"type": "disabled"},
                output_config={"effort": "low"},
                messages=[{"role": "user", "content": user_message}],
            )
        except anthropic.APITimeoutError:
            logger.error("Savol: API timeout")
            return None
        except anthropic.RateLimitError:
            logger.error("Savol: rate limit (429)")
            return None
        except anthropic.APIConnectionError:
            logger.error("Savol: ulanish xatosi")
            return None
        except anthropic.APIStatusError as e:
            logger.error("Savol: API xatosi (status %s)", e.status_code)
            return None
        except Exception:
            logger.error("Savol: kutilmagan xato", exc_info=True)
            return None

        javob = "".join(b.text for b in response.content if b.type == "text").strip()
        return javob or None
