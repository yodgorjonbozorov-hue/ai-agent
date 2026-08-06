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

# Baza yo'li config'dan init_db chaqirilганda beriladi
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
"""


async def init_db(db_path: str) -> None:
    """Bazani yaratadi va sxemani qo'llaydi."""
    set_db_path(db_path)
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.executescript(_SCHEMA)
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
                (group_id, user_id, user_name, date, raw_text, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (group_id, user_id, user_name, date, raw_text, status, _now_iso(tz)),
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
) -> None:
    """Hisobotni AI tahlili natijalari bilan yangilaydi (2-bosqichda ishlatiladi)."""
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            UPDATE reports
            SET status = ?, ai_score = ?, ai_summary = ?, missing_parts = ?,
                has_problem = ?, problem_text = ?
            WHERE id = ?
            """,
            (
                status,
                ai_score,
                ai_summary,
                json.dumps(missing_parts, ensure_ascii=False),
                1 if has_problem else 0,
                problem_text,
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
