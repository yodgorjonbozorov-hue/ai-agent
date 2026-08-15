"""
reporter.py — kunlik (va keyinchalik haftalik) xulosa tuzish.

1-bosqichda xulosa AI'siz: faqat qaysi guruh hisobot yubordi/yubormadi.
2-bosqichda AI xulosalari (ai_summary, has_problem) qo'shiladi.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from statistics import mean
from typing import Any
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
    E'tibor talab qiladigan bandlar (has_problem) alohida ro'yxatda beriladi.
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


async def missing_groups_today(tz: ZoneInfo) -> list[dict[str, Any]]:
    """
    So'rov (18:00) yuborilgan, lekin hali hisobot yubormagan faol guruhlar.
    Eslatma va eskalatsiya joblari shu ro'yxatdan foydalanadi.
    """
    date = today_str(tz)
    groups = await db.get_all_groups(only_active=True)
    missing: list[dict[str, Any]] = []
    for g in groups:
        gid = int(g["id"])
        # Faqat so'rov yuborilgan guruhlar (so'rov vaqti kelmaganlarni tegmaymiz)
        if not await db.has_log(gid, date, "request"):
            continue
        if await db.get_latest_report(gid, date) is None:
            missing.append(g)
    return missing


async def build_weekly_analysis(tz: ZoneInfo) -> str:
    """
    Haftalik tahlil (oxirgi 7 kun): har guruhning hisobot berish foizi,
    o'rtacha AI bahosi, takrorlanuvchi muammolar va intizom reytingi.
    """
    today = datetime.now(tz).date()
    start = today - timedelta(days=6)  # 7 kunlik oyna (bugun ham kiradi)
    start_str = start.strftime("%Y-%m-%d")
    end_str = today.strftime("%Y-%m-%d")

    groups = await db.get_all_groups(only_active=True)
    reports = await db.get_reports_range(start_str, end_str)
    request_dates = await db.get_log_dates_range(start_str, end_str, "request")

    # Kunlik "oxirgisi asosiy": (group_id, date) -> hisobot (created_at bo'yicha oxirgi)
    latest: dict[tuple[int, str], dict[str, Any]] = {}
    for r in reports:
        key = (int(r["group_id"]), r["date"])
        prev = latest.get(key)
        if prev is None or r["created_at"] >= prev["created_at"]:
            latest[key] = r

    # Guruh bo'yicha so'rov yuborilgan kunlar soni
    req_days: dict[int, set[str]] = {}
    for gid, d in request_dates:
        req_days.setdefault(gid, set()).add(d)

    # Har guruh uchun ko'rsatkichlarni hisoblaymiz
    stats: list[dict[str, Any]] = []
    all_problems: list[str] = []

    for g in groups:
        gid = int(g["id"])
        name = g.get("name") or f"Guruh {gid}"

        group_reports = [v for (k_gid, _), v in latest.items() if k_gid == gid]
        report_days = len(group_reports)
        request_day_count = len(req_days.get(gid, set()))
        denom = max(request_day_count, report_days)  # 100% dan oshmasligi uchun
        percent = round(report_days / denom * 100) if denom else 0

        scores = [r["ai_score"] for r in group_reports if r.get("ai_score")]
        avg_score = mean(scores) if scores else None

        for r in group_reports:
            if r.get("has_problem"):
                ptext = (r.get("problem_text") or "").strip()
                if ptext:
                    all_problems.append(f"{name}: {ptext}")

        stats.append(
            {
                "name": name,
                "percent": percent,
                "avg_score": avg_score,
            }
        )

    # Intizom reytingi: foiz bo'yicha, keyin o'rtacha baho bo'yicha
    stats.sort(
        key=lambda s: (s["percent"], s["avg_score"] or 0),
        reverse=True,
    )
    lines = [
        texts.weekly_group_line(i, s["name"], s["percent"], s["avg_score"])
        for i, s in enumerate(stats, start=1)
    ]

    period = f"{start.strftime('%d.%m')} – {today.strftime('%d.%m.%Y')}"
    return texts.admin_weekly(period, lines, all_problems)
