from .core import db

_VALID_PREF_FIELDS = {"signal_filter", "quiet_start", "quiet_end", "min_volume", "price_threshold"}

_DEFAULT_PREFS = {
    "signal_filter": "all",
    "quiet_start": None,
    "quiet_end": None,
    "min_volume": None,
    "price_threshold": None,
}


async def add_subscriber(chat_id: int, username: str = None):
    await db.execute(
        "INSERT INTO subscribers (chat_id, username) VALUES ($1, $2) ON CONFLICT (chat_id) DO NOTHING",
        chat_id, username,
    )
    await db.execute(
        "INSERT INTO preferences (chat_id) VALUES ($1) ON CONFLICT (chat_id) DO NOTHING",
        chat_id,
    )


async def remove_subscriber(chat_id: int):
    await db.execute("DELETE FROM subscribers WHERE chat_id = $1", chat_id)


async def get_all_subscribers() -> list[int]:
    rows = await db.fetchall("SELECT chat_id FROM subscribers")
    return [r["chat_id"] for r in rows]


async def get_subscriber_info(chat_id: int) -> dict | None:
    return await db.fetchone(
        "SELECT chat_id, username, joined_at FROM subscribers WHERE chat_id = $1", chat_id
    )


async def count_subscribers() -> int:
    row = await db.fetchone("SELECT COUNT(*) AS count FROM subscribers")
    return row["count"] if row else 0


async def get_preferences(chat_id: int) -> dict:
    row = await db.fetchone("SELECT * FROM preferences WHERE chat_id = $1", chat_id)
    return dict(row) if row else dict(_DEFAULT_PREFS)


async def upsert_preference(chat_id: int, field: str, value):
    if field not in _VALID_PREF_FIELDS:
        raise ValueError(f"Invalid preference field: {field}")
    await db.upsert(
        f"INSERT INTO preferences (chat_id, {field}) VALUES ($1, $2) "
        f"ON CONFLICT (chat_id) DO UPDATE SET {field} = $2",
        f"INSERT INTO preferences (chat_id, {field}) VALUES (?, ?) "
        f"ON CONFLICT(chat_id) DO UPDATE SET {field} = excluded.{field}",
        chat_id, value,
    )


async def get_all_subscriber_preferences() -> list[dict]:
    return await db.fetchall("""
        SELECT s.chat_id,
               COALESCE(p.signal_filter, 'all') AS signal_filter,
               p.quiet_start, p.quiet_end, p.min_volume, p.price_threshold
        FROM subscribers s
        LEFT JOIN preferences p ON s.chat_id = p.chat_id
    """)
