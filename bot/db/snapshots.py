from datetime import datetime, timedelta, timezone
from bot.config import LOOKBACK_MINUTES
from .core import db


async def insert_snapshot(market_id: str, market_name: str, price: float, volume: float, slug: str = None):
    await db.execute(
        "INSERT INTO snapshots (market_id, market_name, price, volume, slug) VALUES ($1, $2, $3, $4, $5)",
        market_id, market_name, price, volume, slug,
    )


async def get_snapshot_lookback(market_id: str) -> dict | None:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)
    return await db.fetchone(
        "SELECT * FROM snapshots WHERE market_id = $1 AND timestamp <= $2 ORDER BY timestamp DESC LIMIT 1",
        market_id, cutoff,
    )


async def get_recent_snapshots(market_id: str, n: int = 10) -> list[dict]:
    return await db.fetchall(
        "SELECT * FROM snapshots WHERE market_id = $1 ORDER BY timestamp DESC LIMIT $2",
        market_id, n,
    )


async def get_top_movers(n: int = 5) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)
    if db.is_postgres:
        sql = """
            WITH latest AS (
                SELECT DISTINCT ON (market_id) market_id, market_name, price, volume, slug
                FROM snapshots ORDER BY market_id, timestamp DESC
            ),
            lookback AS (
                SELECT DISTINCT ON (market_id) market_id, price AS old_price
                FROM snapshots WHERE timestamp <= $1
                ORDER BY market_id, timestamp DESC
            )
            SELECT l.market_id, l.market_name, l.price, l.volume, l.slug,
                   (l.price - lb.old_price) AS price_change
            FROM latest l JOIN lookback lb ON l.market_id = lb.market_id
            ORDER BY ABS(l.price - lb.old_price) DESC LIMIT $2
        """
    else:
        sql = """
            WITH latest AS (
                SELECT s.market_id, s.market_name, s.price, s.volume, s.slug
                FROM snapshots s
                INNER JOIN (SELECT market_id, MAX(timestamp) AS ts FROM snapshots GROUP BY market_id) m
                    ON s.market_id = m.market_id AND s.timestamp = m.ts
            ),
            lookback AS (
                SELECT s.market_id, s.price AS old_price
                FROM snapshots s
                INNER JOIN (
                    SELECT market_id, MAX(timestamp) AS ts FROM snapshots
                    WHERE timestamp <= ? GROUP BY market_id
                ) m ON s.market_id = m.market_id AND s.timestamp = m.ts
            )
            SELECT l.market_id, l.market_name, l.price, l.volume, l.slug,
                   (l.price - lb.old_price) AS price_change
            FROM latest l JOIN lookback lb ON l.market_id = lb.market_id
            ORDER BY ABS(l.price - lb.old_price) DESC LIMIT ?
        """
    return await db.fetchall(sql, cutoff, n)


async def search_market_snapshot(query: str) -> list[dict]:
    if db.is_postgres:
        sql = """
            SELECT DISTINCT ON (market_id) market_id, market_name, price, volume, slug
            FROM snapshots WHERE market_name ILIKE $1
            ORDER BY market_id, timestamp DESC LIMIT 5
        """
    else:
        sql = """
            SELECT s.market_id, s.market_name, s.price, s.volume, s.slug
            FROM snapshots s
            INNER JOIN (
                SELECT market_id, MAX(timestamp) AS ts FROM snapshots
                WHERE LOWER(market_name) LIKE LOWER(?) GROUP BY market_id
            ) m ON s.market_id = m.market_id AND s.timestamp = m.ts
            LIMIT 5
        """
    return await db.fetchall(sql, query)


async def prune_old_snapshots(days: int = 7) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return await db.execute("DELETE FROM snapshots WHERE timestamp < $1", cutoff)
