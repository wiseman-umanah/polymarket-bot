import re
import asyncpg
import aiosqlite
from bot.config import DATABASE_URL, SQLITE_PATH


def _to_sqlite(sql: str) -> str:
    """Translate PostgreSQL $1/$2/... placeholders to SQLite ?."""
    return re.sub(r'\$\d+', '?', sql)


class Database:
    def __init__(self):
        self._pool = None
        self.is_postgres = bool(DATABASE_URL)

    async def init(self):
        if self.is_postgres:
            self._pool = await asyncpg.create_pool(DATABASE_URL)
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS snapshots (
                        id          BIGSERIAL PRIMARY KEY,
                        market_id   TEXT NOT NULL,
                        market_name TEXT NOT NULL,
                        price       REAL NOT NULL,
                        volume      REAL NOT NULL,
                        slug        TEXT,
                        timestamp   TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
                await conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_snapshots_market_ts ON snapshots (market_id, timestamp DESC)"
                )
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        id          BIGSERIAL PRIMARY KEY,
                        market_id   TEXT NOT NULL,
                        signal_type TEXT NOT NULL,
                        sent_at     TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS subscribers (
                        chat_id   BIGINT PRIMARY KEY,
                        username  TEXT,
                        joined_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS preferences (
                        chat_id         BIGINT PRIMARY KEY,
                        signal_filter   TEXT DEFAULT 'all',
                        quiet_start     SMALLINT,
                        quiet_end       SMALLINT,
                        min_volume      REAL,
                        price_threshold REAL
                    )
                """)
        else:
            async with aiosqlite.connect(SQLITE_PATH) as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS snapshots (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        market_id   TEXT NOT NULL,
                        market_name TEXT NOT NULL,
                        price       REAL NOT NULL,
                        volume      REAL NOT NULL,
                        slug        TEXT,
                        timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_snapshots_market_ts ON snapshots (market_id, timestamp DESC)"
                )
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        market_id   TEXT NOT NULL,
                        signal_type TEXT NOT NULL,
                        sent_at     DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS subscribers (
                        chat_id   INTEGER PRIMARY KEY,
                        username  TEXT,
                        joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS preferences (
                        chat_id         INTEGER PRIMARY KEY,
                        signal_filter   TEXT DEFAULT 'all',
                        quiet_start     INTEGER,
                        quiet_end       INTEGER,
                        min_volume      REAL,
                        price_threshold REAL
                    )
                """)
                await conn.commit()

    async def fetchone(self, sql: str, *args) -> dict | None:
        if self.is_postgres:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(sql, *args)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(SQLITE_PATH) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute(_to_sqlite(sql), args) as cur:
                    row = await cur.fetchone()
                    return dict(row) if row else None

    async def fetchall(self, sql: str, *args) -> list[dict]:
        if self.is_postgres:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(sql, *args)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(SQLITE_PATH) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute(_to_sqlite(sql), args) as cur:
                    return [dict(r) for r in await cur.fetchall()]

    async def execute(self, sql: str, *args) -> int:
        if self.is_postgres:
            async with self._pool.acquire() as conn:
                result = await conn.execute(sql, *args)
                try:
                    return int(result.split()[-1])
                except (ValueError, IndexError):
                    return 0
        else:
            async with aiosqlite.connect(SQLITE_PATH) as conn:
                cur = await conn.execute(_to_sqlite(sql), args)
                await conn.commit()
                return cur.rowcount

    async def upsert(self, pg_sql: str, sqlite_sql: str, *args):
        """Execute an upsert where ON CONFLICT syntax differs between backends."""
        if self.is_postgres:
            async with self._pool.acquire() as conn:
                await conn.execute(pg_sql, *args)
        else:
            async with aiosqlite.connect(SQLITE_PATH) as conn:
                await conn.execute(sqlite_sql, args)
                await conn.commit()


db = Database()
