from datetime import datetime

import aiosqlite

from bot.database.db import get_db_path


# ---------- Админы (те, кто может добавлять ДЗ) ----------

async def add_admin(user_id: int, username: str | None, full_name: str, added_by: int) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """
            INSERT INTO admins (user_id, username, full_name, added_by, added_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name
            """,
            (user_id, username, full_name, added_by, datetime.now().isoformat()),
        )
        await db.commit()


async def remove_admin(user_id: int) -> bool:
    async with aiosqlite.connect(get_db_path()) as db:
        cursor = await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await db.commit()
        return cursor.rowcount > 0


async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(get_db_path()) as db:
        cursor = await db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row is not None


async def list_admins() -> list[dict]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM admins ORDER BY added_at DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ---------- Предметы ----------

async def list_subjects() -> list[dict]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM subjects ORDER BY sort_order ASC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_subject(subject_id: int) -> dict | None:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_subject_by_name(name: str) -> dict | None:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM subjects WHERE name = ?", (name,))
        row = await cursor.fetchone()
        return dict(row) if row else None


# ---------- Домашние задания ----------

async def add_homework(
    subject_id: int,
    description: str,
    added_by: int,
    added_by_name: str,
    file_id: str | None = None,
    file_type: str | None = None,
) -> int:
    now = datetime.now()
    async with aiosqlite.connect(get_db_path()) as db:
        cursor = await db.execute(
            """
            INSERT INTO homework
                (subject_id, description, file_id, file_type, added_by, added_by_name, created_at, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                subject_id,
                description,
                file_id,
                file_type,
                added_by,
                added_by_name,
                now.isoformat(),
                now.strftime("%Y-%m-%d"),
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def get_subjects_with_homework() -> list[dict]:
    """Предметы, по которым уже есть хотя бы одно ДЗ."""
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT DISTINCT s.id, s.name, s.sort_order
            FROM subjects s
            JOIN homework h ON h.subject_id = s.id
            ORDER BY s.sort_order ASC
            """
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_dates_for_subject(subject_id: int) -> list[str]:
    async with aiosqlite.connect(get_db_path()) as db:
        cursor = await db.execute(
            """
            SELECT DISTINCT created_date FROM homework
            WHERE subject_id = ?
            ORDER BY created_date DESC
            """,
            (subject_id,),
        )
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def get_homework_by_subject_date(subject_id: int, date: str) -> list[dict]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT h.*, s.name AS subject_name FROM homework h
            JOIN subjects s ON s.id = h.subject_id
            WHERE h.subject_id = ? AND h.created_date = ?
            ORDER BY h.created_at ASC
            """,
            (subject_id, date),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_homework(homework_id: int) -> dict | None:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT h.*, s.name AS subject_name FROM homework h
            JOIN subjects s ON s.id = h.subject_id
            WHERE h.id = ?
            """,
            (homework_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def delete_homework(homework_id: int) -> bool:
    async with aiosqlite.connect(get_db_path()) as db:
        cursor = await db.execute("DELETE FROM homework WHERE id = ?", (homework_id,))
        await db.commit()
        return cursor.rowcount > 0


# ---------- Темы и очередь (метаязыки) ----------

async def reset_meta_topics(subject_id: int, count: int) -> None:
    """Полностью заменяет набор тем предмета новым (1..count), очередь обнуляется."""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "DELETE FROM meta_queue WHERE topic_id IN (SELECT id FROM meta_topics WHERE subject_id = ?)",
            (subject_id,),
        )
        await db.execute("DELETE FROM meta_topics WHERE subject_id = ?", (subject_id,))
        await db.executemany(
            "INSERT INTO meta_topics (subject_id, number, created_at) VALUES (?, ?, ?)",
            [(subject_id, number, now) for number in range(1, count + 1)],
        )
        await db.commit()


async def list_meta_topics_with_counts(subject_id: int) -> list[dict]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT t.id, t.number, COUNT(q.id) AS people_count
            FROM meta_topics t
            LEFT JOIN meta_queue q ON q.topic_id = t.id
            WHERE t.subject_id = ?
            GROUP BY t.id
            ORDER BY t.number ASC
            """,
            (subject_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_meta_topic(topic_id: int) -> dict | None:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM meta_topics WHERE id = ?", (topic_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_meta_queue_entry(subject_id: int, user_id: int) -> dict | None:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT q.topic_id, t.number
            FROM meta_queue q
            JOIN meta_topics t ON t.id = q.topic_id
            WHERE t.subject_id = ? AND q.user_id = ?
            """,
            (subject_id, user_id),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_queue_position(topic_id: int, user_id: int) -> int | None:
    async with aiosqlite.connect(get_db_path()) as db:
        cursor = await db.execute(
            "SELECT user_id FROM meta_queue WHERE topic_id = ? ORDER BY joined_at ASC",
            (topic_id,),
        )
        rows = await cursor.fetchall()
        for index, row in enumerate(rows, start=1):
            if row[0] == user_id:
                return index
        return None


async def join_meta_queue(topic_id: int, user_id: int, user_name: str) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "INSERT INTO meta_queue (topic_id, user_id, user_name, joined_at) VALUES (?, ?, ?, ?)",
            (topic_id, user_id, user_name, datetime.now().isoformat()),
        )
        await db.commit()


async def leave_meta_queue(subject_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(get_db_path()) as db:
        cursor = await db.execute(
            """
            DELETE FROM meta_queue
            WHERE user_id = ? AND topic_id IN (SELECT id FROM meta_topics WHERE subject_id = ?)
            """,
            (user_id, subject_id),
        )
        await db.commit()
        return cursor.rowcount > 0
