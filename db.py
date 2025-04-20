import aiosqlite
from datetime import datetime

DB_PATH = "zoo_bot_data.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS results (
                user_id INTEGER,
                animal TEXT,
                datetime TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                user_id INTEGER,
                text TEXT,
                datetime TEXT
            )
        """)
        await db.commit()


async def get_result(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT animal FROM results WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def save_result(user_id: int, animal: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO results (user_id, animal, datetime) VALUES (?, ?, ?)",
            (user_id, animal, datetime.now().isoformat())
        )
        await db.commit()


async def save_feedback(user_id: int, text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO feedback (user_id, text, datetime) VALUES (?, ?, ?)",
            (user_id, text, datetime.now().isoformat())
        )
        await db.commit()

