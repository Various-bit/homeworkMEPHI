import aiosqlite

from bot.constants import META_SUBJECT_NAME, META_TOPICS_COUNT, SUBJECTS

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

        # Старая модель очереди метаязыков (произвольное число тем, без
        # занятий) несовместима с новой (7 фиксированных тем × 3 занятия).
        # Если БД ещё в старой схеме — пересоздаём эти две таблицы.
        cursor = await db.execute("PRAGMA table_info(meta_queue)")
        existing_columns = [row[1] for row in await cursor.fetchall()]
        if existing_columns and "session_position" not in existing_columns:
            await db.execute("DROP TABLE IF EXISTS meta_queue")
            await db.execute("DROP TABLE IF EXISTS meta_topics")

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS meta_topics (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id  INTEGER NOT NULL REFERENCES subjects(id),
                number      INTEGER NOT NULL,
                created_at  TEXT NOT NULL,
                UNIQUE(subject_id, number)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS meta_queue (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id          INTEGER NOT NULL REFERENCES meta_topics(id),
                session_position  INTEGER NOT NULL,
                user_id           INTEGER NOT NULL,
                user_name         TEXT NOT NULL,
                joined_at         TEXT NOT NULL,
                UNIQUE(topic_id, session_position, user_id)
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

        cursor = await db.execute("SELECT id FROM subjects WHERE name = ?", (META_SUBJECT_NAME,))
        row = await cursor.fetchone()
        if row is not None:
            meta_subject_id = row[0]
            for number in range(1, META_TOPICS_COUNT + 1):
                await db.execute(
                    """
                    INSERT INTO meta_topics (subject_id, number, created_at)
                    VALUES (?, ?, datetime('now'))
                    ON CONFLICT(subject_id, number) DO NOTHING
                    """,
                    (meta_subject_id, number),
                )

        await db.commit()
