import aiosqlite

from bot.constants import SUBJECTS

_db_path: str = "bot/database/homework.db"


def set_db_path(path: str) -> None:
    global _db_path
    _db_path = path


def get_db_path() -> str:
    return _db_path


async def init_db() -> None:
    async with aiosqlite.connect(_db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                full_name   TEXT,
                added_by    INTEGER,
                added_at    TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS subjects (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS homework (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id    INTEGER NOT NULL REFERENCES subjects(id),
                description   TEXT NOT NULL,
                file_id       TEXT,
                file_type     TEXT,
                added_by      INTEGER NOT NULL,
                added_by_name TEXT,
                created_at    TEXT NOT NULL,
                created_date  TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS meta_topics (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id  INTEGER NOT NULL REFERENCES subjects(id),
                number      INTEGER NOT NULL,
                created_at  TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS meta_queue (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id    INTEGER NOT NULL REFERENCES meta_topics(id),
                user_id     INTEGER NOT NULL,
                user_name   TEXT NOT NULL,
                joined_at   TEXT NOT NULL,
                UNIQUE(topic_id, user_id)
            )
            """
        )
        for order, name in enumerate(SUBJECTS):
            await db.execute(
                """
                INSERT INTO subjects (name, sort_order) VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET sort_order = excluded.sort_order
                """,
                (name, order),
            )

        # Предметы, убранные из SUBJECTS, удаляем из справочника — но только
        # если по ним ещё нет ни ДЗ, ни тем очереди (иначе рискуем сломать FK).
        placeholders = ",".join("?" for _ in SUBJECTS)
        await db.execute(
            f"""
            DELETE FROM subjects
            WHERE name NOT IN ({placeholders})
              AND id NOT IN (SELECT DISTINCT subject_id FROM homework)
              AND id NOT IN (SELECT DISTINCT subject_id FROM meta_topics)
            """,
            SUBJECTS,
        )
        await db.commit()
