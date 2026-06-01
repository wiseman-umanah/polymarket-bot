from .core import db
from .snapshots import (
    insert_snapshot,
    get_snapshot_lookback,
    get_recent_snapshots,
    get_top_movers,
    search_market_snapshot,
    prune_old_snapshots,
)
from .alerts import (
    insert_alert,
    get_last_alert,
    get_recent_alerts,
    count_alerts_today,
)
from .subscribers import (
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
    await db.init()
