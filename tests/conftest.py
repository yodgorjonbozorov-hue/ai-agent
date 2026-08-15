"""
conftest.py — testlar uchun umumiy fixture'lar.

Har bir test uchun vaqtinchalik (tmp_path) SQLite bazasi yaratiladi, shuning
uchun testlar bir-biriga va haqiqiy `data/bot.db` ga umuman tegmaydi.
"""

from __future__ import annotations

import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

# Loyiha ildizini import yo'liga qo'shamiz (tests/ ichidan ishga tushirilganda ham)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import database as db  # noqa: E402


TZ = ZoneInfo("Asia/Tashkent")


@pytest.fixture
async def database(tmp_path):
    """Har bir test uchun toza, vaqtinchalik baza."""
    path = tmp_path / "test.db"
    await db.init_db(str(path))
    yield db
    db.set_db_path("data/bot.db")  # global holatni tiklaymiz


@pytest.fixture
async def group_id(database):
    """Bitta tayyor test guruhi va uning ichki id si."""
    return await database.add_or_update_group(
        chat_id=-1001234567890, name="Test guruh", tz=TZ
    )
