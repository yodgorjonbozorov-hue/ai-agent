"""
texts.py — foydalanuvchiga ko'rinadigan barcha matn shablonlari.

Barcha matnlar o'zbek tilida (lotin). Kod ichida matn qattiq yozilmaydi —
shu yerdan f-string shablon sifatida olinadi. Bu tarjima va o'zgartirishni
osonlashtiradi.
"""

from __future__ import annotations

from typing import Any

# --------------------------------------------------------------------------
# Guruhga yuboriladigan xabarlar
# --------------------------------------------------------------------------

# 09:00 — ertalabki xabar (vazifalar bilan)
def morning_with_tasks(tasks: list[str]) -> str:
    lines = "\n".join(f"{i}. {t}" for i, t in enumerate(tasks, start=1))
    return (
        "☀️ Xayrli tong!\n\n"
        "Bugungi vazifalar:\n"
        f"{lines}\n\n"
        "Omad tilaymiz! Kun oxirida hisobot kutamiz."
    )


# 09:00 — vazifa yo'q bo'lsa umumiy eslatma
MORNING_NO_TASKS = (
    "☀️ Xayrli tong!\n\n"
    "Bugun uchun alohida vazifa belgilanmagan.\n"
    "Rejadagi ishlarni davom ettiring — kun oxirida hisobot kutamiz."
)

# 18:00 — hisobot so'rovi shabloni
REPORT_REQUEST = (
    "📋 Bugungi hisobot vaqti\n\n"
    "Iltimos, quyidagi tartibda yozing:\n\n"
    "1️⃣ Bajarilgan ishlar:\n"
    "2️⃣ Bajarilmagani va sababi:\n"
    "3️⃣ Muammolar / kerak bo'lgan yordam:\n"
    "4️⃣ Ertangi reja:"
)

# 18:30 — 1-eslatma (muloyim)
REMINDER_SOFT = (
    "🔔 Eslatma\n\n"
    "Hisobotingizni hali ko'rmadik. Iltimos, imkoni bo'lsa yuboring — "
    "rahmat! 🙏"
)

# 20:00 — 2-eslatma (takroriy)
REMINDER_FIRM = (
    "⏰ Takroriy eslatma\n\n"
    "Bugungi hisobot hali kelmadi. Iltimos, kun yakunlanishidan oldin "
    "yuboring."
)

# Hisobot qabul qilinganda (AI: to'liq)
REPORT_ACCEPTED = "✅ Hisobot qabul qilindi, rahmat!"


# Hisobot to'liq bo'lmaganda (AI: yetishmagan qismlar bor)
def report_incomplete(missing: list[str]) -> str:
    parts = ", ".join(missing) if missing else "ba'zi qismlar"
    return (
        f"Rahmat! Lekin {parts} qismi yo'q — to'ldirib yuborasizmi? 🙏"
    )


# Hisobot bazaga tushdi, lekin AI ishlamadi (pending)
REPORT_RECEIVED_PLAIN = "✅ Hisobotingiz qabul qilindi, rahmat!"


# --------------------------------------------------------------------------
# Adminга yuboriladigan xabarlar
# --------------------------------------------------------------------------

def admin_new_group(name: str, chat_id: int) -> str:
    return (
        "🆕 Yangi guruh qo'shildi\n\n"
        f"Nomi: {name}\n"
        f"Chat ID: {chat_id}\n\n"
        "Sozlash uchun: /vazifa va /vaqt komandalaridan foydalaning."
    )


def admin_daily_summary(
    date_str: str,
    submitted: int,
    total: int,
    lines: list[str],
    attention: list[str],
) -> str:
    """
    22:00 kunlik xulosa (1-bosqichda AI'siz — faqat kim yubordi/yubormadi).
    lines — har bir guruh uchun bitta qator.
    attention — e'tibor talab qiladigan bandlar (bo'lishi mumkin).
    """
    body = "\n".join(lines) if lines else "Hech qanday guruh ro'yxatda yo'q."
    text = (
        f"📊 {date_str} — Kunlik xulosa\n\n"
        f"Hisobot berdi: {submitted}/{total}\n\n"
        f"{body}"
    )
    if attention:
        att = "\n".join(f"• {a}" for a in attention)
        text += f"\n\n🔴 E'tibor talab qiladi:\n{att}"
    return text


def admin_problem_alert(group_name: str, problem: str) -> str:
    return (
        "🔴 DIQQAT — muammo signali\n\n"
        f"Guruh: {group_name}\n"
        f"Muammo: {problem}"
    )


def admin_escalation(missing_groups: list[str]) -> str:
    """20:00 eskalatsiya — javob bermagan guruhlar ro'yxati."""
    if not missing_groups:
        return "✅ Barcha guruhlar hisobot yubordi."
    lst = "\n".join(f"• {g}" for g in missing_groups)
    return (
        "⚠️ Hozircha javob bermaganlar:\n\n"
        f"{lst}"
    )


# --------------------------------------------------------------------------
# Admin komandalari uchun matnlar
# --------------------------------------------------------------------------

ADMIN_START = (
    "🤖 Disney Navoiy — Hisobot Bot\n\n"
    "Mavjud komandalar:\n"
    "/guruhlar — guruhlar ro'yxati va holati\n"
    "/vazifa — guruhga bugungi vazifa qo'shish\n"
    "/vaqt — guruh vaqtlarini o'zgartirish\n"
    "/hisobot — bugungi holat\n"
    "/haftalik — haftalik reyting\n"
    "/pauza <guruh_id> — guruhni to'xtatish\n"
    "/faol <guruh_id> — guruhni yoqish\n"
    "/matn <guruh_id> — guruhning bugungi hisobot matni"
)

NOT_ADMIN = "⛔ Bu bot faqat admin uchun."


def group_list_line(g: dict[str, Any], has_report: bool) -> str:
    """/guruhlar dagi bitta guruh qatori."""
    status = "🟢" if g.get("is_active") else "⏸"
    report_mark = "✅ hisobot bor" if has_report else "❌ hisobot yo'q"
    return (
        f"{status} [{g['id']}] {g.get('name') or 'nomsiz'} — {report_mark}\n"
        f"    ⏰ ertalab {g['morning_time']} / so'rov {g['request_time']}"
    )
