from sqlmodel import SQLModel
from .engine import engine
from . import models  # noqa: F401 — registers tables on SQLModel.metadata
from .snapshots import (
    snapshot_repo,
    insert_snapshot,
    get_snapshot_lookback,
    get_recent_snapshots,
    get_top_movers,
    search_market_snapshot,
    prune_old_snapshots,
)
from .alerts import (
    alert_repo,
    insert_alert,
    get_last_alert,
    get_recent_alerts,
    count_alerts_today,
)
from .subscribers import (
    subscriber_repo,
    add_subscriber,
    remove_subscriber,
    get_all_subscribers,
    get_subscriber_info,
    count_subscribers,
    get_preferences,
    upsert_preference,
    get_all_subscriber_preferences,
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
