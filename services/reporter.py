"""
reporter.py — kunlik (va keyinchalik haftalik) xulosa tuzish.

1-bosqichda xulosa AI'siz: faqat qaysi guruh hisobot yubordi/yubormadi.
2-bosqichda AI xulosalari (ai_summary, has_problem) qo'shiladi.
"""

from __future__ import annotations

import json
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


def _json_royxat(qiymat: Any) -> list[str]:
    """Bazadagi JSON ustunni xavfsiz ro'yxatga aylantiradi."""
    if not qiymat:
        return []
    try:
        natija = json.loads(qiymat)
    except (TypeError, ValueError):
        return []
    return [str(x) for x in natija] if isinstance(natija, list) else []


def today_weekday(tz: ZoneInfo) -> int:
    """Bugungi hafta kuni: 1 = dushanba ... 7 = yakshanba (ISO)."""
    return datetime.now(tz).isoweekday()


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

        # AI xulosasi bo'lsa ko'rsatamiz, aks holda oddiy belgi
        summary = (report.get("ai_summary") or "").strip()
        has_problem = bool(report.get("has_problem"))

        if has_problem and summary:
            mark = "⚠️"
        else:
            mark = "✅"

        rasm = " 📷" if report.get("has_photo") else ""
        if summary:
            qator = f"{mark} {name}{rasm} — {summary}"
        else:
            qator = f"{mark} {name}{rasm} — hisobot qabul qilindi"

        # Vazifa nazorati: qaysi vazifa bajarildi, qaysi biri qolib ketdi
        qator += texts.vazifa_holati(
            _json_royxat(report.get("done_tasks")),
            _json_royxat(report.get("undone_tasks")),
        )
        lines.append(qator)

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


async def build_assistant_context(tz: ZoneInfo, kunlar: int = 7) -> str:
    """
    Admin savollariga javob berish uchun bazadan qisqa holat lavhasini
    yig'adi. Matn modelga beriladi, shuning uchun ixcham va aniq.
    """
    bugun = today_str(tz)
    hozir = datetime.now(tz).date()
    boshi = (hozir - timedelta(days=kunlar - 1)).strftime("%Y-%m-%d")

    groups = await db.get_all_groups()
    reports = await db.get_reports_for_date(bugun)
    oraliq = await db.get_reports_range(boshi, bugun)
    sorov_kunlari = await db.get_log_dates_range(boshi, bugun, "request")

    qatorlar: list[str] = [
        f"Bugun: {bugun} ({pretty_date(tz)})",
        f"Oraliq: {boshi} — {bugun}",
        "",
        "GURUHLAR VA BUGUNGI HOLAT:",
    ]

    for g in groups:
        gid = int(g["id"])
        nomi = g.get("name") or f"Guruh {gid}"
        holat = "faol" if g.get("is_active") else "pauzada"
        qatorlar.append(f"[{gid}] {nomi} ({holat})")

        vazifalar = await db.get_tasks(gid, bugun)
        if vazifalar:
            qatorlar.append(
                "  Bugungi vazifalar: "
                + "; ".join(v["text"] for v in vazifalar)
            )

        doimiy = await db.get_recurring_tasks(gid)
        if doimiy:
            qatorlar.append(
                "  Doimiy vazifalar: " + "; ".join(v["text"] for v in doimiy)
            )

        r = reports.get(gid)
        if r is None:
            qatorlar.append("  Bugungi hisobot: YO'Q")
        else:
            baho = r.get("ai_score")
            qatorlar.append(
                f"  Bugungi hisobot: BOR"
                + (f", baho {baho}/5" if baho else "")
                + (", rasm bilan" if r.get("has_photo") else "")
                + f", yuborgan: {r.get('user_name') or 'nomalum'}"
            )
            if (r.get("ai_summary") or "").strip():
                qatorlar.append(f"  Qisqacha: {r['ai_summary'].strip()}")
            bajarilmagan = _json_royxat(r.get("undone_tasks"))
            if bajarilmagan:
                qatorlar.append(
                    "  Bajarilmagan vazifalar: " + "; ".join(bajarilmagan)
                )
            if r.get("has_problem") and (r.get("problem_text") or "").strip():
                qatorlar.append(f"  MUAMMO: {r['problem_text'].strip()}")
            matn = (r.get("raw_text") or "").strip()
            if matn:
                qisqa = matn if len(matn) <= 400 else matn[:400] + "..."
                qatorlar.append(f"  Hisobot matni: {qisqa}")

    # Oraliq bo'yicha statistika
    oxirgilar: dict[tuple[int, str], dict[str, Any]] = {}
    for r in oraliq:
        kalit = (int(r["group_id"]), r["date"])
        oldingi = oxirgilar.get(kalit)
        if oldingi is None or r["created_at"] >= oldingi["created_at"]:
            oxirgilar[kalit] = r

    sorov_soni: dict[int, set[str]] = {}
    for gid, d in sorov_kunlari:
        sorov_soni.setdefault(gid, set()).add(d)

    qatorlar += ["", f"OXIRGI {kunlar} KUN:"]
    for g in groups:
        gid = int(g["id"])
        nomi = g.get("name") or f"Guruh {gid}"
        guruh_hisobotlari = [v for (k, _), v in oxirgilar.items() if k == gid]
        kunlar_soni = len(guruh_hisobotlari)
        sorovlar = len(sorov_soni.get(gid, set()))
        bahalar = [r["ai_score"] for r in guruh_hisobotlari if r.get("ai_score")]
        ortacha = f"{mean(bahalar):.1f}" if bahalar else "yo'q"
        qatorlar.append(
            f"[{gid}] {nomi}: {kunlar_soni} kun hisobot berdi "
            f"({sorovlar} kun so'ralgan), o'rtacha baho {ortacha}"
        )
        muammolar = [
            f"{r['date']}: {(r.get('problem_text') or '').strip()}"
            for r in guruh_hisobotlari
            if r.get("has_problem") and (r.get("problem_text") or "").strip()
        ]
        for m in sorted(muammolar):
            qatorlar.append(f"  Muammo {m}")

    return "\n".join(qatorlar)
