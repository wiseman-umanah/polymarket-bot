from datetime import datetime, timezone
from .core import db


async def insert_alert(market_id: str, signal_type: str):
    await db.execute(
        "INSERT INTO alerts (market_id, signal_type) VALUES ($1, $2)",
        market_id, signal_type,
    )


async def get_last_alert(market_id: str, signal_type: str) -> dict | None:
    return await db.fetchone(
        "SELECT * FROM alerts WHERE market_id = $1 AND signal_type = $2 ORDER BY sent_at DESC LIMIT 1",
        market_id, signal_type,
    )


async def get_recent_alerts(n: int = 5) -> list[dict]:
    if db.is_postgres:
        sql = """
            SELECT a.market_id, a.signal_type, a.sent_at,
                   COALESCE(s.market_name, a.market_id) AS market_name
            FROM alerts a
            LEFT JOIN LATERAL (
                SELECT market_name FROM snapshots
                WHERE market_id = a.market_id ORDER BY timestamp DESC LIMIT 1
            ) s ON true
            ORDER BY a.sent_at DESC LIMIT $1
        """
    else:
        sql = """
            SELECT a.market_id, a.signal_type, a.sent_at,
                   COALESCE(s.market_name, a.market_id) AS market_name
            FROM alerts a
            LEFT JOIN (
                SELECT market_id, market_name, MAX(timestamp) FROM snapshots GROUP BY market_id
            ) s ON a.market_id = s.market_id
            ORDER BY a.sent_at DESC LIMIT ?
        """
    return await db.fetchall(sql, n)


async def count_alerts_today() -> int:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    row = await db.fetchone("SELECT COUNT(*) AS count FROM alerts WHERE sent_at >= $1", today_start)
    return row["count"] if row else 0
