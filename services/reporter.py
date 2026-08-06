"""
reporter.py — kunlik (va keyinchalik haftalik) xulosa tuzish.

1-bosqichda xulosa AI'siz: faqat qaysi guruh hisobot yubordi/yubormadi.
2-bosqichda AI xulosalari (ai_summary, has_problem) qo'shiladi.
"""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import database as db
import texts

logger = logging.getLogger(__name__)


def today_str(tz: ZoneInfo) -> str:
    """Bugungi sanani YYYY-MM-DD ko'rinishida qaytaradi."""
    return datetime.now(tz).strftime("%Y-%m-%d")


def pretty_date(tz: ZoneInfo) -> str:
    """Bugungi sanani DD.MM.YYYY ko'rinishida qaytaradi (xulosa sarlavhasi uchun)."""
    return datetime.now(tz).strftime("%d.%m.%Y")


async def build_daily_summary(tz: ZoneInfo) -> str:
    """
    22:00 kunlik xulosa matnini tuzadi.

    Har bir faol guruh uchun bitta qator:
      ✅ Nomi — AI qisqa xulosa (bo'lsa) / hisobot bor
      ❌ Nomi — hisobot yo'q
    E'tibor talab qiladigan bandlar (has_problem) alohida ro'yxatда beriladi.
    """
    date = today_str(tz)
    groups = await db.get_all_groups(only_active=True)
    reports = await db.get_reports_for_date(date)

    lines: list[str] = []
    attention: list[str] = []
    submitted = 0

    for g in groups:
        gid = int(g["id"])
        name = g.get("name") or f"Guruh {gid}"
        report = reports.get(gid)

        if report is None:
            lines.append(f"❌ {name} — hisobot yo'q")
            continue

        submitted += 1

        # AI xulosasi bo'lsa ko'rsatamiz (2-bosqich), aks holda oddiy belgi
        summary = (report.get("ai_summary") or "").strip()
        has_problem = bool(report.get("has_problem"))

        if has_problem and summary:
            mark = "⚠️"
        else:
            mark = "✅"

        if summary:
            lines.append(f"{mark} {name} — {summary}")
        else:
            lines.append(f"{mark} {name} — hisobot qabul qilindi")

        if has_problem:
            problem = (report.get("problem_text") or "").strip()
            attention.append(f"{name}: {problem or 'muammo qayd etildi'}")

    return texts.admin_daily_summary(
        date_str=pretty_date(tz),
        submitted=submitted,
        total=len(groups),
        lines=lines,
        attention=attention,
    )
