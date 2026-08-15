"""
texts.py — foydalanuvchiga ko'rinadigan barcha matn shablonlari.

Barcha matnlar o'zbek tilida (lotin). Kod ichida matn qattiq yozilmaydi —
shu yerdan f-string shablon sifatida olinadi. Bu tarjima va o'zgartirishni
osonlashtiradi.
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

# Rasm izohsiz yoki juda qisqa izoh bilan kelganda
RASM_IZOHSIZ = "(rasm — izohsiz)"
RASM_QABUL_QILINDI = (
    "📷 Rasm qabul qilindi, rahmat!\n"
    "Imkon bo'lsa qisqacha izoh ham yozing — nima bajarilgani aniq bo'lishi uchun."
)


# --------------------------------------------------------------------------
# Adminga yuboriladigan xabarlar
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


def vazifa_holati(bajarilgan: list[str], bajarilmagan: list[str]) -> str:
    """
    Kunlik xulosadagi vazifa nazorati qatorlari.
    Vazifa belgilanmagan bo'lsa bo'sh matn qaytadi.
    """
    jami = len(bajarilgan) + len(bajarilmagan)
    if jami == 0:
        return ""
    matn = f"\n    📋 {jami} tadan {len(bajarilgan)} tasi bajarildi"
    for v in bajarilmagan:
        matn += f"\n    ❌ {v}"
    return matn


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
    "✍️ Vazifa berish uchun oddiy gap bilan yozing:\n"
    "«Qurilish guruhiga ertaga: devor suvash, pol tayyorlash»\n"
    "«Ta'mirlash guruhiga har kuni xavfsizlik tekshiruvi»\n\n"
    "❓ Savol ham berishingiz mumkin:\n"
    "«Kim bugun hisobot bermadi?»\n"
    "«Disney guruhi nima yozdi?»\n"
    "«Bu hafta qaysi guruh yomon ishlayapti?»\n\n"
    "Qolganini o'zim qilaman: har kuni ertalab vazifalarni yuboraman, "
    "kechqurun hisobot so'rayman, eslatma beraman va 22:00 da sizga "
    "xulosa yuboraman.\n\n"
    "Mavjud komandalar:\n"
    "/guruhlar — guruhlar ro'yxati va holati\n"
    "/doimiy — doimiy (takrorlanuvchi) vazifalar\n"
    "/vazifa — guruhga bugungi vazifa qo'shish (tugmalar bilan)\n"
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
NO_GROUPS = "Hozircha birorta guruh ro'yxatda yo'q."
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
# Erkin matn bilan vazifa berish va doimiy vazifalar
# --------------------------------------------------------------------------

_KUN_QISQA = {1: "Du", 2: "Se", 3: "Ch", 4: "Pa", 5: "Ju", 6: "Sh", 7: "Ya"}


def kunlar_matni(kunlar: list[int]) -> str:
    """[1,2,3,4,5,6] -> 'Du, Se, Ch, Pa, Ju, Sh' (yoki 'har kuni')."""
    if not kunlar or sorted(kunlar) == [1, 2, 3, 4, 5, 6, 7]:
        return "har kuni"
    if sorted(kunlar) == [1, 2, 3, 4, 5, 6]:
        return "ish kunlari (Du–Sh)"
    return ", ".join(_KUN_QISQA.get(k, str(k)) for k in sorted(kunlar))


def tasdiq_sorovi(bloklar: list[str]) -> str:
    """Saqlashdan oldin adminga ko'rsatiladigan xulosa."""
    return (
        "📝 Shunday tushundim:\n\n"
        + "\n\n".join(bloklar)
        + "\n\nTo'g'rimi?"
    )


def tasdiq_bloki(
    group_name: str,
    tur: str,
    sana: str,
    kunlar: list[int],
    vazifalar: list[str],
) -> str:
    """Bitta guruh uchun tasdiq matni."""
    ro_yxat = "\n".join(f"   {i}. {v}" for i, v in enumerate(vazifalar, start=1))
    if tur == "doimiy":
        sarlavha = f"🔁 {group_name} — doimiy ({kunlar_matni(kunlar)})"
    else:
        sarlavha = f"📌 {group_name} — {sana}"
    return f"{sarlavha}\n{ro_yxat}"


def yangi_vazifalar_guruhga(vazifalar: list[str]) -> str:
    """Vazifa bugunga bo'lsa, guruhga darhol yuboriladigan xabar."""
    ro_yxat = "\n".join(f"{i}. {v}" for i, v in enumerate(vazifalar, start=1))
    return (
        "📌 Yangi vazifa\n\n"
        f"{ro_yxat}\n\n"
        "Kun oxirida hisobot kutamiz."
    )


def vazifalar_saqlandi(
    bir_martalik: int,
    doimiy: int,
    yuborilgan_guruhlar: list[str] | None = None,
    ertalabga: int = 0,
) -> str:
    """Adminga: nima saqlandi va nima allaqachon guruhga ketdi."""
    qatorlar = []
    if bir_martalik:
        qatorlar.append(f"📌 {bir_martalik} ta vazifa saqlandi")
    if doimiy:
        qatorlar.append(f"🔁 {doimiy} ta doimiy vazifa qo'shildi")
    if not qatorlar:
        return "Hech narsa saqlanmadi."

    matn = "✅ " + "\n✅ ".join(qatorlar)

    if yuborilgan_guruhlar:
        ro_yxat = ", ".join(yuborilgan_guruhlar)
        matn += f"\n\n📤 Guruhga hozir yuborildi: {ro_yxat}"
    if ertalabga:
        matn += f"\n\n🕘 {ertalabga} ta vazifa o'z kunida ertalab yuboriladi."
    return matn


GURUHGA_YUBORILMADI = (
    "\n\n⚠️ Ba'zi guruhlarga xabar yuborib bo'lmadi — bot guruhdan "
    "chiqarilgan yoki yozish huquqi yo'q bo'lishi mumkin."
)


TASDIQLASH = "✅ Ha, to'g'ri"
BEKOR_QILISH = "❌ Yo'q, bekor"
TAHLIL_QILINMOQDA = "🤔 O'qiyapman..."
def tushunmadim(savol: str, guruh_nomlari: list[str]) -> str:
    """
    Model tushunmaganda ko'rsatiladigan matn. Mavjud guruh nomlari ham
    ko'rsatiladi — foydalanuvchi qanday yozishni bilib olishi uchun.
    """
    matn = savol or "Tushunmadim — qaysi guruh haqida gapirayotganingizni topa olmadim."
    if guruh_nomlari:
        ro_yxat = "\n".join(f"• {n}" for n in guruh_nomlari)
        matn += f"\n\nMavjud guruhlar:\n{ro_yxat}"
    matn += (
        "\n\nMasalan: «" + (guruh_nomlari[0] if guruh_nomlari else "Qurilish")
        + " guruhiga ertaga: devor suvash, pol tayyorlash»"
    )
    return matn


SAVOLGA_JAVOB_YOQ = (
    "Javob tayyorlay olmadim. Biroz kutib qayta so'rang yoki "
    "/hisobot, /guruhlar, /haftalik komandalaridan foydalaning."
)

AI_ULANMADI = (
    "⚠️ Hozir AI bilan bog'lana olmadim, shuning uchun matnni tushuna olmadim.\n\n"
    "Sabablari: internet uzilishi, API kaliti eskirgan yoki limit tugagan.\n"
    "Vazifani hozir qo'shish uchun /vazifa komandasidan foydalaning."
)
AI_OCHIQ_EMAS = (
    "Erkin matn bilan vazifa berish uchun AI kaliti kerak "
    "(.env dagi ANTHROPIC_API_KEY).\n\n"
    "Hozircha /vazifa komandasidan foydalaning."
)


def doimiy_royxat(guruh_nomi: str, vazifalar: list[dict[str, Any]]) -> str:
    """/doimiy — bitta guruhning doimiy vazifalari."""
    if not vazifalar:
        return f"🔁 {guruh_nomi}: doimiy vazifa yo'q."
    qatorlar = [
        f"   [{v['id']}] {v['text']}  ({kunlar_matni(_kunlar_ajrat(v['weekdays']))})"
        for v in vazifalar
    ]
    return f"🔁 {guruh_nomi}\n" + "\n".join(qatorlar)


def _kunlar_ajrat(weekdays: str) -> list[int]:
    return [int(d) for d in str(weekdays).split(",") if d.strip().isdigit()]


DOIMIY_YOQ = (
    "🔁 Hozircha doimiy vazifa yo'q.\n\n"
    "Qo'shish uchun shunchaki yozing:\n"
    "«Qurilish guruhiga har kuni xavfsizlik tekshiruvi»"
)


def doimiy_ochirildi(text: str) -> str:
    return f"🗑 O'chirildi: {text}"


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
