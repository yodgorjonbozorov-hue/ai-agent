"""
database.py — libSQL (Turso yoki lokal SQLite) baza qatlami.

Bitta kod ikki rejimda ishlaydi:
  - TURSO_DATABASE_URL berilgan bo'lsa  → Turso (bulutdagi libSQL), ma'lumot
    hech qachon yo'qolmaydi (ephemeral hostlarda ham xavfsiz);
  - berilmagan bo'lsa                   → lokal `file:<DB_PATH>` SQLite fayl.

Ikkala holatda ham bir xil `libsql_client` API ishlatiladi, shuning uchun
lokal sinov Turso yo'lini ham to'liq tekshiradi (faqat URL farq qiladi).

ORM yo'q: oddiy SQL yetarli. Barcha funksiyalar asinxron va type hint bilan.
Baza xatolari yashirilmaydi — chaqiruvchi tomon ushlaydi.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

import libsql_client

logger = logging.getLogger(__name__)

# Lokal rejim uchun baza fayli yo'li (init_db da o'rnatiladi)
_DB_PATH: str = "data/bot.db"

# Butun ilova uchun bitta ulanish (init_db da yaratiladi)
_client: Optional[libsql_client.Client] = None


def set_db_path(path: str) -> None:
    """Lokal baza fayli yo'lini o'rnatadi (bot ishga tushganda chaqiriladi)."""
    global _DB_PATH
    _DB_PATH = path


def _client_or_raise() -> libsql_client.Client:
    """Ulanishni qaytaradi; init_db chaqirilmagan bo'lsa xato beradi."""
    if _client is None:
        raise RuntimeError("Baza ishga tushirilmagan — avval init_db() chaqiring.")
    return _client


def _build_client() -> tuple[libsql_client.Client, str]:
    """
    Muhit o'zgaruvchilariga qarab libSQL mijozini quradi.
    (client, rejim_tavsifi) qaytaradi.
    """
    turso_url = os.getenv("TURSO_DATABASE_URL", "").strip()
    if turso_url:
        # Turso: websocket (libsql://) o'rniga HTTPS transportini ishlatamiz —
        # kam trafikли bot uchun barqarorroq (har so'rov mustaqil).
        http_url = turso_url
        if http_url.startswith("libsql://"):
            http_url = "https://" + http_url[len("libsql://"):]
        auth_token = os.getenv("TURSO_AUTH_TOKEN", "").strip() or None
        client = libsql_client.create_client(url=http_url, auth_token=auth_token)
        return client, f"Turso ({http_url})"

    # Lokal fayl rejimi
    Path(_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    client = libsql_client.create_client(url=f"file:{_DB_PATH}")
    return client, f"lokal fayl ({_DB_PATH})"


# --------------------------------------------------------------------------
# Sxema — har bir gap alohida (libSQL executescript ishlatmaydi)
# --------------------------------------------------------------------------

_SCHEMA_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS groups (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id      INTEGER UNIQUE NOT NULL,
        name         TEXT,
        department   TEXT,
        request_time TEXT NOT NULL DEFAULT '18:00',
        morning_time TEXT NOT NULL DEFAULT '09:00',
        is_active    INTEGER NOT NULL DEFAULT 1,
        created_at   TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id  INTEGER NOT NULL,
        date      TEXT NOT NULL,
        text      TEXT NOT NULL,
        FOREIGN KEY (group_id) REFERENCES groups (id)
    )
    """,
    """
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
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS logs (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id   INTEGER,
        date       TEXT NOT NULL,
        type       TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_reports_group_date ON reports (group_id, date)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_group_date  ON tasks (group_id, date)",
    "CREATE INDEX IF NOT EXISTS idx_logs_group_date   ON logs (group_id, date)",
]


async def init_db(db_path: str) -> None:
    """Ulanishni quradi va sxemani qo'llaydi."""
    global _client
    set_db_path(db_path)
    client, mode = _build_client()
    await client.batch(_SCHEMA_STATEMENTS)
    _client = client
    logger.info("Baza tayyor: %s", mode)


async def close_db() -> None:
    """Ulanishni yopadi (bot to'xtaganda chaqiriladi)."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


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
    client = _client_or_raise()
    rs = await client.execute("SELECT id FROM groups WHERE chat_id = ?", [chat_id])
    if rs.rows:
        gid = int(rs.rows[0]["id"])
        await client.execute(
            "UPDATE groups SET name = ?, is_active = 1 WHERE chat_id = ?",
            [name, chat_id],
        )
        return gid

    rs = await client.execute(
        "INSERT INTO groups (chat_id, name, department, created_at) VALUES (?, ?, ?, ?)",
        [chat_id, name, department, _now_iso(tz)],
    )
    return int(rs.last_insert_rowid)


async def get_all_groups(only_active: bool = False) -> list[dict[str, Any]]:
    """Barcha guruhlarni ro'yxat qilib qaytaradi."""
    query = "SELECT * FROM groups"
    if only_active:
        query += " WHERE is_active = 1"
    query += " ORDER BY name COLLATE NOCASE"
    rs = await _client_or_raise().execute(query)
    return [r.asdict() for r in rs.rows]


async def get_group_by_chat_id(chat_id: int) -> Optional[dict[str, Any]]:
    """Telegram chat_id bo'yicha guruhni topadi."""
    rs = await _client_or_raise().execute(
        "SELECT * FROM groups WHERE chat_id = ?", [chat_id]
    )
    return rs.rows[0].asdict() if rs.rows else None


async def get_group_by_id(group_id: int) -> Optional[dict[str, Any]]:
    """Ichki id bo'yicha guruhni topadi."""
    rs = await _client_or_raise().execute(
        "SELECT * FROM groups WHERE id = ?", [group_id]
    )
    return rs.rows[0].asdict() if rs.rows else None


async def set_group_active(group_id: int, is_active: bool) -> None:
    """Guruhni pauza qiladi yoki qayta faollashtiradi."""
    await _client_or_raise().execute(
        "UPDATE groups SET is_active = ? WHERE id = ?",
        [1 if is_active else 0, group_id],
    )


async def update_group_time(group_id: int, field: str, value: str) -> None:
    """Guruhning so'rov yoki ertalabki vaqtini yangilaydi."""
    if field not in ("request_time", "morning_time"):
        raise ValueError(f"Noto'g'ri vaqt maydoni: {field}")
    await _client_or_raise().execute(
        f"UPDATE groups SET {field} = ? WHERE id = ?", [value, group_id]
    )


# --------------------------------------------------------------------------
# tasks — CRUD
# --------------------------------------------------------------------------

async def add_task(group_id: int, date: str, text: str) -> int:
    """Guruh uchun berilgan sanaga vazifa qo'shadi."""
    rs = await _client_or_raise().execute(
        "INSERT INTO tasks (group_id, date, text) VALUES (?, ?, ?)",
        [group_id, date, text],
    )
    return int(rs.last_insert_rowid)


async def get_tasks(group_id: int, date: str) -> list[dict[str, Any]]:
    """Guruhning berilgan sanadagi vazifalarini qaytaradi."""
    rs = await _client_or_raise().execute(
        "SELECT * FROM tasks WHERE group_id = ? AND date = ? ORDER BY id",
        [group_id, date],
    )
    return [r.asdict() for r in rs.rows]


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
    rs = await _client_or_raise().execute(
        """
        INSERT INTO reports
            (group_id, user_id, user_name, date, raw_text, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [group_id, user_id, user_name, date, raw_text, status, _now_iso(tz)],
    )
    return int(rs.last_insert_rowid)


async def update_report_ai(
    report_id: int,
    status: str,
    ai_score: Optional[int],
    ai_summary: str,
    missing_parts: list[str],
    has_problem: bool,
    problem_text: str,
) -> None:
    """Hisobotni AI tahlili natijalari bilan yangilaydi."""
    await _client_or_raise().execute(
        """
        UPDATE reports
        SET status = ?, ai_score = ?, ai_summary = ?, missing_parts = ?,
            has_problem = ?, problem_text = ?
        WHERE id = ?
        """,
        [
            status,
            ai_score,
            ai_summary,
            json.dumps(missing_parts, ensure_ascii=False),
            1 if has_problem else 0,
            problem_text,
            report_id,
        ],
    )


async def get_latest_report(group_id: int, date: str) -> Optional[dict[str, Any]]:
    """Guruhning berilgan sanadagi eng oxirgi hisobotini qaytaradi."""
    rs = await _client_or_raise().execute(
        """
        SELECT * FROM reports
        WHERE group_id = ? AND date = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        [group_id, date],
    )
    return rs.rows[0].asdict() if rs.rows else None


async def get_reports_for_date(date: str) -> dict[int, dict[str, Any]]:
    """
    Berilgan sanadagi barcha guruhlarning eng oxirgi hisobotini qaytaradi.
    Kalit — group_id, qiymat — hisobot dict'i.
    """
    rs = await _client_or_raise().execute(
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
        [date, date],
    )
    result: dict[int, dict[str, Any]] = {}
    for r in rs.rows:
        d = r.asdict()
        result[int(d["group_id"])] = d
    return result


async def get_reports_range(start_date: str, end_date: str) -> list[dict[str, Any]]:
    """
    [start_date, end_date] oralig'idagi barcha hisobotlarni qaytaradi
    (haftalik tahlil uchun). Kunlik 'oxirgisi asosiy' dedublyatsiyasi
    chaqiruvchi tomonda qilinadi.
    """
    rs = await _client_or_raise().execute(
        "SELECT * FROM reports WHERE date >= ? AND date <= ? ORDER BY created_at",
        [start_date, end_date],
    )
    return [r.asdict() for r in rs.rows]


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
    await _client_or_raise().execute(
        "INSERT INTO logs (group_id, date, type, created_at) VALUES (?, ?, ?, ?)",
        [group_id, date, log_type, _now_iso(tz)],
    )


async def has_log(group_id: Optional[int], date: str, log_type: str) -> bool:
    """Berilgan turdagi log allaqachon yozilganini tekshiradi."""
    rs = await _client_or_raise().execute(
        "SELECT 1 FROM logs WHERE group_id IS ? AND date = ? AND type = ? LIMIT 1",
        [group_id, date, log_type],
    )
    return len(rs.rows) > 0


async def get_log_dates_range(
    start_date: str, end_date: str, log_type: str
) -> list[tuple[int, str]]:
    """
    Oraliqда berilgan turdagi loglarning (group_id, date) juftliklarini
    qaytaradi. Haftalik tahlilда 'so'rov yuborilgan kunlar' sonini
    hisoblash uchun ishlatiladi.
    """
    rs = await _client_or_raise().execute(
        "SELECT DISTINCT group_id, date FROM logs "
        "WHERE date >= ? AND date <= ? AND type = ? AND group_id IS NOT NULL",
        [start_date, end_date, log_type],
    )
    return [(int(r[0]), r[1]) for r in rs.rows]
