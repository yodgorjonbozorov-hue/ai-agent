"""
texts.py — ZAXIRA matn shablonlari.

Botning odamlarga boradigan matnlarini odatda AI yozadi (services/ai.py).
Bu yerdagi shablonlar faqat AI ishlamaganda ishlatiladi: API kaliti yo'q,
timeout, rate limit yoki javobni o'qib bo'lmadi. Shunda ham bot jim
qolmaydi va hisobot yo'qolmaydi.

Adminга boradigan ro'yxat/reyting matnlari esa doim shu yerdan olinadi —
raqamlar aniq bo'lishi kerak, AI faqat ularga sharh qo'shadi.

Barcha matnlar o'zbek tilida (lotin).
"""

from __future__ import annotations

from typing import Any, Optional

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

# Savolga javob berish kerak edi, lekin AI javob bermadi
AI_UNAVAILABLE = (
    "Hozir javob bera olmadim — biroz kutib qayta yozing. "
    "Muammo takrorlansa, adminга xabar bering."
)


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
    "/matn <guruh_id> — guruhning bugungi hisobot matni\n"
    "/debug — qo'lda test komandalari"
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


# --------------------------------------------------------------------------
# Interaktiv admin komandalari (/vazifa, /vaqt, /pauza, /faol, /matn)
# --------------------------------------------------------------------------

CHOOSE_GROUP = "Guruhni tanlang:"
NO_GROUPS = "Hozircha birorta guruh ro'yxatда yo'q."
CANCELLED = "Bekor qilindi."

VAZIFA_ENTER = "✍️ Endi vazifa matnini yuboring (bir nechta bo'lsa har birini alohida qatorda):"


def vazifa_added(group_name: str, count: int) -> str:
    return f"✅ {group_name} guruhiga bugunga {count} ta vazifa qo'shildi."


VAQT_CHOOSE_FIELD = "Qaysi vaqtni o'zgartiramiz?"
VAQT_FIELD_REQUEST = "📋 Hisobot so'rovi vaqti"
VAQT_FIELD_MORNING = "☀️ Ertalabki xabar vaqti"
VAQT_ENTER = "🕐 Yangi vaqtni HH:MM formatida yuboring (masalan 18:00):"
VAQT_INVALID = "❌ Noto'g'ri format. HH:MM ko'rinishida yuboring (masalan 09:30)."


def vaqt_updated(group_name: str, field_label: str, value: str) -> str:
    return f"✅ {group_name}: {field_label} → {value} ga o'zgartirildi."


GROUP_NOT_FOUND = "❌ Bunday ID li guruh topilmadi."
USAGE_PAUZA = "Foydalanish: /pauza <guruh_id>"
USAGE_FAOL = "Foydalanish: /faol <guruh_id>"
USAGE_MATN = "Foydalanish: /matn <guruh_id>"


def group_paused(name: str) -> str:
    return f"⏸ {name} guruhi vaqtincha to'xtatildi."


def group_activated(name: str) -> str:
    return f"🟢 {name} guruhi qayta faollashtirildi."


def report_text_view(name: str, report: Optional[dict[str, Any]]) -> str:
    """/matn — guruhning bugungi to'liq hisobot matni."""
    if not report:
        return f"📄 {name}: bugun hisobot yo'q."
    status_map = {
        "accepted": "✅ qabul qilingan",
        "incomplete": "⚠️ to'liq emas",
        "pending": "⏳ tekshirilmagan",
    }
    status = status_map.get(report.get("status", ""), report.get("status", ""))
    score = report.get("ai_score")
    score_line = f"\nBaho: {score}/5" if score else ""
    author = report.get("user_name") or "Noma'lum"
    return (
        f"📄 {name} — bugungi hisobot\n"
        f"Yuborgan: {author}\n"
        f"Holat: {status}{score_line}\n"
        f"{'─' * 20}\n"
        f"{report.get('raw_text', '')}"
    )


# --------------------------------------------------------------------------
# Haftalik tahlil
# --------------------------------------------------------------------------

def admin_weekly(period: str, lines: list[str], problems: list[str]) -> str:
    """Haftalik tahlil matni (intizom reytingi bilan)."""
    body = "\n\n".join(lines) if lines else "Ma'lumot yo'q."
    text = (
        f"📈 Haftalik tahlil ({period})\n\n"
        f"🏆 Intizom reytingi:\n\n{body}"
    )
    if problems:
        prob = "\n".join(f"• {p}" for p in problems)
        text += f"\n\n🔁 Takrorlanuvchi muammolar:\n{prob}"
    return text


def weekly_group_line(
    rank: int,
    name: str,
    percent: int,
    avg_score: Optional[float],
) -> str:
    """Haftalik reytingdagi bitta guruh qatori."""
    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
    avg_txt = f"{avg_score:.1f}/5" if avg_score is not None else "—"
    return (
        f"{medal} {name}\n"
        f"    Hisobot berish: {percent}% | O'rtacha baho: {avg_txt}"
    )


# --------------------------------------------------------------------------
# Debug komandalar (qo'lda test qilish uchun)
# --------------------------------------------------------------------------

DEBUG_HELP = (
    "🧪 Debug komandalar (jadvalni kutmasdan qo'lda ishga tushirish):\n\n"
    "/test_xulosa — kunlik xulosani ko'rsatish\n"
    "/test_haftalik — haftalik tahlilni adminga yuborish\n"
    "/test_ertalabki <id> — guruhga ertalabki xabarni yuborish\n"
    "/test_sorov <id> — guruhga hisobot so'rovini yuborish\n"
    "/test_eslatma — hozir hisobot bermaganlarga eslatma yuborish"
)

USAGE_TEST_MORNING = "Foydalanish: /test_ertalabki <guruh_id>"
USAGE_TEST_REQUEST = "Foydalanish: /test_sorov <guruh_id>"
TEST_DONE = "✅ Test bajarildi."
TEST_SENT_GROUP = "✅ Guruhga yuborildi."
