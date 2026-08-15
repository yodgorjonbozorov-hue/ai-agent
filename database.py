"""
database.py — SQLite baza sxemasi va CRUD funksiyalari.

ORM ishlatilmaydi: oddiy SQL + aiosqlite yetarli.
Barcha funksiyalar asinxron va type hint bilan yozilgan.
Tashqi chaqiruvlar (baza) try/except ichida emas — chaqiruvchi tomon
xatoni ushlaydi, chunki baza xatosi kritik va yashirilmasligi kerak;
lekin ba'zi "yumshoq" o'qishlar himoyalangan.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

import aiosqlite

logger = logging.getLogger(__name__)

# Baza yo'li config'dan init_db chaqirilganda beriladi
_DB_PATH: str = "data/bot.db"


def set_db_path(path: str) -> None:
    """Baza fayli yo'lini o'rnatadi (bot ishga tushganda chaqiriladi)."""
    global _DB_PATH
    _DB_PATH = path


# --------------------------------------------------------------------------
# Sxema
# --------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS groups (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id      INTEGER UNIQUE NOT NULL,
    name         TEXT,
    department   TEXT,
    request_time TEXT NOT NULL DEFAULT '18:00',
    morning_time TEXT NOT NULL DEFAULT '09:00',
    is_active    INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id  INTEGER NOT NULL,
    date      TEXT NOT NULL,
    text      TEXT NOT NULL,
    FOREIGN KEY (group_id) REFERENCES groups (id)
);

-- Doimiy (takrorlanuvchi) vazifalar. Bir marta yoziladi, har kuni ertalab
-- shu kunning `tasks` jadvaliga avtomatik ko'chiriladi.
-- weekdays: ISO hafta kunlari vergul bilan (1 = dushanba ... 7 = yakshanba)
CREATE TABLE IF NOT EXISTS recurring_tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id   INTEGER NOT NULL,
    text       TEXT NOT NULL,
    weekdays   TEXT NOT NULL DEFAULT '1,2,3,4,5,6,7',
    is_active  INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY (group_id) REFERENCES groups (id)
);

CREATE TABLE IF NOT EXISTS reports (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id      INTEGER NOT NULL,
    user_id       INTEGER,
    user_name     TEXT,
    date          TEXT NOT NULL,
    raw_text      TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    ai_score      INTEGER,
    ai_summary    TEXT,
    missing_parts TEXT,
    has_problem   INTEGER NOT NULL DEFAULT 0,
    problem_text  TEXT,
    done_tasks    TEXT,
    undone_tasks  TEXT,
    has_photo     INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL,
    FOREIGN KEY (group_id) REFERENCES groups (id)
);

CREATE TABLE IF NOT EXISTS logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id   INTEGER,
    date       TEXT NOT NULL,
    type       TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_group_date ON reports (group_id, date);
CREATE INDEX IF NOT EXISTS idx_tasks_group_date  ON tasks (group_id, date);
CREATE INDEX IF NOT EXISTS idx_logs_group_date   ON logs (group_id, date);
CREATE INDEX IF NOT EXISTS idx_recurring_group    ON recurring_tasks (group_id);
"""


# Keyingi bosqichlarda qo'shilgan ustunlar.
# CREATE TABLE IF NOT EXISTS ishlab turgan bazaga yangi ustun qo'shmaydi,
# shuning uchun ularni alohida tekshirib qo'shamiz. Bu mavjud ma'lumotga
# tegmaydi.
_MIGRATIONS: list[tuple[str, str, str]] = [
    # (jadval, ustun, ta'rif)
    ("reports", "done_tasks", "TEXT"),      # bajarilgan vazifalar (JSON)
    ("reports", "undone_tasks", "TEXT"),    # bajarilmagan vazifalar (JSON)
    ("reports", "has_photo", "INTEGER NOT NULL DEFAULT 0"),
]


async def _apply_migrations(db: aiosqlite.Connection) -> None:
    """Yetishmayotgan ustunlarni qo'shadi (ishlab turgan baza uchun)."""
    for jadval, ustun, tarif in _MIGRATIONS:
        cur = await db.execute(f"PRAGMA table_info({jadval})")
        mavjud = {row[1] for row in await cur.fetchall()}
        if ustun not in mavjud:
            await db.execute(f"ALTER TABLE {jadval} ADD COLUMN {ustun} {tarif}")
            logger.info("Bazaga ustun qo'shildi: %s.%s", jadval, ustun)


async def init_db(db_path: str) -> None:
    """Bazani yaratadi, sxemani qo'llaydi va yetishmayotgan ustunlarni qo'shadi."""
    set_db_path(db_path)
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await _apply_migrations(db)
        await db.commit()
    logger.info("Baza tayyor: %s", _DB_PATH)


def _now_iso(tz: Optional[ZoneInfo] = None) -> str:
    """Hozirgi vaqtni ISO formatda qaytaradi."""
    return datetime.now(tz).isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# groups — CRUD
# --------------------------------------------------------------------------

async def add_or_update_group(
    chat_id: int,
    name: str,
    department: str = "",
    tz: Optional[ZoneInfo] = None,
) -> int:
    """
    Guruhni qo'shadi yoki mavjud bo'lsa nomini yangilaydi.
    Guruhning ichki id sini qaytaradi.
    """
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT id FROM groups WHERE chat_id = ?", (chat_id,)
        )
        row = await cur.fetchone()
        if row is not None:
            await db.execute(
                "UPDATE groups SET name = ?, is_active = 1 WHERE chat_id = ?",
                (name, chat_id),
            )
            await db.commit()
            return int(row["id"])

        cur = await db.execute(
            """
            INSERT INTO groups (chat_id, name, department, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (chat_id, name, department, _now_iso(tz)),
        )
        await db.commit()
        return int(cur.lastrowid)


async def get_all_groups(only_active: bool = False) -> list[dict[str, Any]]:
    """Barcha guruhlarni ro'yxat qilib qaytaradi."""
    query = "SELECT * FROM groups"
    if only_active:
        query += " WHERE is_active = 1"
    query += " ORDER BY name COLLATE NOCASE"
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(query)
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_group_by_chat_id(chat_id: int) -> Optional[dict[str, Any]]:
    """Telegram chat_id bo'yicha guruhni topadi."""
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM groups WHERE chat_id = ?", (chat_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_group_by_id(group_id: int) -> Optional[dict[str, Any]]:
    """Ichki id bo'yicha guruhni topadi."""
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def set_group_active(group_id: int, is_active: bool) -> None:
    """Guruhni pauza qiladi yoki qayta faollashtiradi."""
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            "UPDATE groups SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, group_id),
        )
        await db.commit()


async def update_group_time(group_id: int, field: str, value: str) -> None:
    """Guruhning so'rov yoki ertalabki vaqtini yangilaydi."""
    if field not in ("request_time", "morning_time"):
        raise ValueError(f"Noto'g'ri vaqt maydoni: {field}")
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            f"UPDATE groups SET {field} = ? WHERE id = ?", (value, group_id)
        )
        await db.commit()


# --------------------------------------------------------------------------
# tasks — CRUD
# --------------------------------------------------------------------------

async def add_task(group_id: int, date: str, text: str) -> int:
    """Guruh uchun berilgan sanaga vazifa qo'shadi."""
    async with aiosqlite.connect(_DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO tasks (group_id, date, text) VALUES (?, ?, ?)",
            (group_id, date, text),
        )
        await db.commit()
        return int(cur.lastrowid)


async def get_tasks(group_id: int, date: str) -> list[dict[str, Any]]:
    """Guruhning berilgan sanadagi vazifalarini qaytaradi."""
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM tasks WHERE group_id = ? AND date = ? ORDER BY id",
            (group_id, date),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def add_task_if_absent(group_id: int, date: str, text: str) -> bool:
    """
    Vazifani faqat shu guruh/sana uchun hali mavjud bo'lmasa qo'shadi.
    Doimiy vazifalarni ko'chirishda ishlatiladi — bot kun davomida qayta
    ishga tushsa ham vazifalar ikki marta qo'shilmaydi.
    Qo'shilgan bo'lsa True qaytaradi.
    """
    async with aiosqlite.connect(_DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM tasks WHERE group_id = ? AND date = ? AND text = ? LIMIT 1",
            (group_id, date, text),
        )
        if await cur.fetchone() is not None:
            return False
        await db.execute(
            "INSERT INTO tasks (group_id, date, text) VALUES (?, ?, ?)",
            (group_id, date, text),
        )
        await db.commit()
        return True


# --------------------------------------------------------------------------
# recurring_tasks — doimiy vazifalar
# --------------------------------------------------------------------------

def _weekdays_to_str(weekdays: Optional[list[int]]) -> str:
    """[1,2,3] -> '1,2,3'. Bo'sh bo'lsa — har kuni."""
    if not weekdays:
        return "1,2,3,4,5,6,7"
    tozalangan = sorted({int(d) for d in weekdays if 1 <= int(d) <= 7})
    return ",".join(str(d) for d in tozalangan) or "1,2,3,4,5,6,7"


async def add_recurring_task(
    group_id: int,
    text: str,
    weekdays: Optional[list[int]] = None,
    tz: Optional[ZoneInfo] = None,
) -> int:
    """Doimiy vazifa qo'shadi va uning id sini qaytaradi."""
    async with aiosqlite.connect(_DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO recurring_tasks (group_id, text, weekdays, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (group_id, text, _weekdays_to_str(weekdays), _now_iso(tz)),
        )
        await db.commit()
        return int(cur.lastrowid)


async def get_recurring_tasks(
    group_id: Optional[int] = None, only_active: bool = True
) -> list[dict[str, Any]]:
    """Doimiy vazifalarni qaytaradi (guruh bo'yicha yoki hammasini)."""
    query = "SELECT * FROM recurring_tasks"
    shartlar: list[str] = []
    args: list[Any] = []
    if group_id is not None:
        shartlar.append("group_id = ?")
        args.append(group_id)
    if only_active:
        shartlar.append("is_active = 1")
    if shartlar:
        query += " WHERE " + " AND ".join(shartlar)
    query += " ORDER BY group_id, id"

    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(query, tuple(args))
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def delete_recurring_task(task_id: int) -> None:
    """Doimiy vazifani o'chiradi (butunlay)."""
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("DELETE FROM recurring_tasks WHERE id = ?", (task_id,))
        await db.commit()


async def apply_recurring_tasks(group_id: int, date: str, weekday: int) -> int:
    """
    Guruhning shu hafta kuniga tegishli doimiy vazifalarini `tasks` ga
    ko'chiradi. Nechta yangi vazifa qo'shilganini qaytaradi.

    Ertalabki xabar yuborilishidan oldin chaqiriladi, shuning uchun
    takroriy chaqiruvga chidamli (add_task_if_absent).
    """
    qoshilgan = 0
    for r in await get_recurring_tasks(group_id, only_active=True):
        kunlar = {int(d) for d in str(r["weekdays"]).split(",") if d.strip().isdigit()}
        if weekday in kunlar and await add_task_if_absent(group_id, date, r["text"]):
            qoshilgan += 1
    return qoshilgan


# --------------------------------------------------------------------------
# reports — CRUD
# --------------------------------------------------------------------------

async def add_report(
    group_id: int,
    user_id: int,
    user_name: str,
    date: str,
    raw_text: str,
    status: str = "pending",
    has_photo: bool = False,
    tz: Optional[ZoneInfo] = None,
) -> int:
    """
    Yangi hisobotni bazaga yozadi.
    Bir kunda bir necha hisobot kelsa — hammasi saqlanadi,
    eng oxirgisi asosiy deb hisoblanadi (created_at bo'yicha).
    """
    async with aiosqlite.connect(_DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO reports
                (group_id, user_id, user_name, date, raw_text, status,
                 has_photo, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (group_id, user_id, user_name, date, raw_text, status,
             1 if has_photo else 0, _now_iso(tz)),
        )
        await db.commit()
        return int(cur.lastrowid)


async def update_report_ai(
    report_id: int,
    status: str,
    ai_score: Optional[int],
    ai_summary: str,
    missing_parts: list[str],
    has_problem: bool,
    problem_text: str,
    done_tasks: Optional[list[str]] = None,
    undone_tasks: Optional[list[str]] = None,
) -> None:
    """Hisobotni AI tahlili natijalari bilan yangilaydi."""
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            UPDATE reports
            SET status = ?, ai_score = ?, ai_summary = ?, missing_parts = ?,
                has_problem = ?, problem_text = ?,
                done_tasks = ?, undone_tasks = ?
            WHERE id = ?
            """,
            (
                status,
                ai_score,
                ai_summary,
                json.dumps(missing_parts, ensure_ascii=False),
                1 if has_problem else 0,
                problem_text,
                json.dumps(done_tasks or [], ensure_ascii=False),
                json.dumps(undone_tasks or [], ensure_ascii=False),
                report_id,
            ),
        )
        await db.commit()


async def get_latest_report(group_id: int, date: str) -> Optional[dict[str, Any]]:
    """Guruhning berilgan sanadagi eng oxirgi hisobotini qaytaradi."""
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT * FROM reports
            WHERE group_id = ? AND date = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (group_id, date),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_reports_for_date(date: str) -> dict[int, dict[str, Any]]:
    """
    Berilgan sanadagi barcha guruhlarning eng oxirgi hisobotini qaytaradi.
    Kalit — group_id, qiymat — hisobot dict'i.
    """
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT r.* FROM reports r
            INNER JOIN (
                SELECT group_id, MAX(created_at) AS mx
                FROM reports WHERE date = ?
                GROUP BY group_id
            ) latest
            ON r.group_id = latest.group_id AND r.created_at = latest.mx
            WHERE r.date = ?
            """,
            (date, date),
        )
        rows = await cur.fetchall()
        result: dict[int, dict[str, Any]] = {}
        for r in rows:
            d = dict(r)
            result[int(d["group_id"])] = d
        return result


async def get_reports_range(start_date: str, end_date: str) -> list[dict[str, Any]]:
    """
    [start_date, end_date] oralig'idagi barcha hisobotlarni qaytaradi
    (haftalik tahlil uchun). Kunlik 'oxirgisi asosiy' dedublyatsiyasi
    chaqiruvchi tomonda qilinadi.
    """
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM reports WHERE date >= ? AND date <= ? "
            "ORDER BY created_at",
            (start_date, end_date),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# logs — eslatma/eskalatsiya tarixi
# --------------------------------------------------------------------------

async def add_log(
    group_id: Optional[int],
    date: str,
    log_type: str,
    tz: Optional[ZoneInfo] = None,
) -> None:
    """Yuborilgan eslatma yoki eskalatsiyani tarixga yozadi."""
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            "INSERT INTO logs (group_id, date, type, created_at) VALUES (?, ?, ?, ?)",
            (group_id, date, log_type, _now_iso(tz)),
        )
        await db.commit()


async def has_log(group_id: Optional[int], date: str, log_type: str) -> bool:
    """Berilgan turdagi log allaqachon yozilganini tekshiradi (takrorlashning oldini olish)."""
    async with aiosqlite.connect(_DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM logs WHERE group_id IS ? AND date = ? AND type = ? LIMIT 1",
            (group_id, date, log_type),
        )
        row = await cur.fetchone()
        return row is not None


async def get_log_dates_range(
    start_date: str, end_date: str, log_type: str
) -> list[tuple[int, str]]:
    """
    Oraliqda berilgan turdagi loglarning (group_id, date) juftliklarini
    qaytaradi. Haftalik tahlilda 'so'rov yuborilgan kunlar' sonini
    hisoblash uchun ishlatiladi.
    """
    async with aiosqlite.connect(_DB_PATH) as db:
        cur = await db.execute(
            "SELECT DISTINCT group_id, date FROM logs "
            "WHERE date >= ? AND date <= ? AND type = ? AND group_id IS NOT NULL",
            (start_date, end_date, log_type),
        )
        rows = await cur.fetchall()
        return [(int(r[0]), r[1]) for r in rows]
