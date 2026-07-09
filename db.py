import aiosqlite
from datetime import datetime, timedelta

from config import DB_PATH, START_BONUS, RECHECK_HOURS


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                username TEXT,
                balance REAL DEFAULT 0,
                frozen_balance REAL DEFAULT 0,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                chat_id INTEGER,
                username TEXT,
                title TEXT,
                price REAL DEFAULT 1.0,
                active INTEGER DEFAULT 1,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel_id INTEGER,
                status TEXT DEFAULT 'frozen',
                reward REAL,
                cost REAL,
                created_at TEXT,
                check_at TEXT,
                UNIQUE(user_id, channel_id)
            )
        """)
        await db.commit()


# ---------- USERS ----------

async def get_or_create_user(tg_id: int, username: str | None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
        row = await cur.fetchone()
        if row:
            return dict(row), False
        now = datetime.utcnow().isoformat()
        await db.execute(
            "INSERT INTO users (tg_id, username, balance, frozen_balance, created_at) VALUES (?,?,?,?,?)",
            (tg_id, username, START_BONUS, 0, now),
        )
        await db.commit()
        cur = await db.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
        row = await cur.fetchone()
        return dict(row), True


async def get_user(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def change_balance(tg_id: int, delta: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE tg_id=?", (delta, tg_id))
        await db.commit()


async def change_frozen(tg_id: int, delta: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET frozen_balance = frozen_balance + ? WHERE tg_id=?", (delta, tg_id))
        await db.commit()


# ---------- CHANNELS ----------

async def add_channel(owner_id: int, chat_id: int, username: str, title: str, price: float):
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.utcnow().isoformat()
        cur = await db.execute(
            "INSERT INTO channels (owner_id, chat_id, username, title, price, active, created_at) "
            "VALUES (?,?,?,?,?,1,?)",
            (owner_id, chat_id, username, title, price, now),
        )
        await db.commit()
        return cur.lastrowid


async def get_channel(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM channels WHERE id=?", (channel_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_user_channels(owner_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM channels WHERE owner_id=? ORDER BY id", (owner_id,))
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def channel_exists_for_owner(owner_id: int, chat_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id FROM channels WHERE owner_id=? AND chat_id=?", (owner_id, chat_id)
        )
        return (await cur.fetchone()) is not None


async def set_channel_active(channel_id: int, active: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE channels SET active=? WHERE id=?", (1 if active else 0, channel_id))
        await db.commit()


async def delete_channel(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM channels WHERE id=?", (channel_id,))
        await db.execute("DELETE FROM subscriptions WHERE channel_id=?", (channel_id,))
        await db.commit()


async def count_completed_tasks(user_id: int) -> int:
    """Сколько заданий (подписок на чужие каналы) пользователь довёл до подтверждения."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM subscriptions WHERE user_id=? AND status='confirmed'", (user_id,)
        )
        row = await cur.fetchone()
        return row[0] if row else 0


async def count_user_channels(owner_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM channels WHERE owner_id=?", (owner_id,))
        row = await cur.fetchone()
        return row[0] if row else 0


async def count_confirmed_subs(channel_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM subscriptions WHERE channel_id=? AND status='confirmed'", (channel_id,)
        )
        row = await cur.fetchone()
        return row[0] if row else 0


# ---------- TASKS / SUBSCRIPTIONS ----------

async def get_random_task(user_id: int):
    """Находит канал для задания: не свой, активный, ещё не взятый этим юзером,
    у владельца хватает баланса на цену подписки."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT c.* FROM channels c
            JOIN users u ON u.tg_id = c.owner_id
            WHERE c.active = 1
              AND c.owner_id != ?
              AND u.balance >= c.price
              AND c.id NOT IN (
                  SELECT channel_id FROM subscriptions WHERE user_id = ?
              )
            ORDER BY RANDOM()
            LIMIT 1
            """,
            (user_id, user_id),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def create_frozen_subscription(user_id: int, channel: dict, reward: float):
    now = datetime.utcnow()
    check_at = now + timedelta(hours=RECHECK_HOURS)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO subscriptions (user_id, channel_id, status, reward, cost, created_at, check_at) "
            "VALUES (?,?,'frozen',?,?,?,?)",
            (user_id, channel["id"], reward, channel["price"], now.isoformat(), check_at.isoformat()),
        )
        await db.commit()
    await change_frozen(user_id, reward)
    await change_balance(channel["owner_id"], -channel["price"])


async def get_due_rechecks():
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM subscriptions WHERE status='frozen' AND check_at <= ?", (now,)
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def confirm_subscription(sub_id: int, user_id: int, reward: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE subscriptions SET status='confirmed' WHERE id=?", (sub_id,))
        await db.commit()
    await change_frozen(user_id, -reward)
    await change_balance(user_id, reward)


async def cancel_subscription(sub_id: int, user_id: int, owner_id: int, reward: float, cost: float):
    async with aiosqlite.connect(DB_PATH) as db:
        # удаляем запись, чтобы пользователь мог позже честно выполнить это же задание заново
        await db.execute("DELETE FROM subscriptions WHERE id=?", (sub_id,))
        await db.commit()
    await change_frozen(user_id, -reward)
    await change_balance(owner_id, cost)  # возврат баллов владельцу канала
