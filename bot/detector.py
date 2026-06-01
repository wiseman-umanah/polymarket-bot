from bot.config import PRICE_CHANGE_THRESHOLD, VOLUME_SPIKE_MULTIPLIER, VOLUME_AVERAGE_WINDOW
from bot.db import get_snapshot_lookback, get_recent_snapshots


async def check_price_movement(market_id: str, current_price: float) -> tuple[bool, float]:
    """Returns (triggered, signed_change). Triggered when abs change >= threshold vs lookback snapshot."""
    try:
        old = await get_snapshot_lookback(market_id)
        if not old:
            return False, 0.0
        signed_change = current_price - old["price"]
        return abs(signed_change) >= PRICE_CHANGE_THRESHOLD, signed_change
    except Exception as e:
        print(f"[ERROR] check_price_movement failed for {market_id}: {e}")
        return False, 0.0


async def check_volume_spike(market_id: str, current_volume: float) -> bool:
    """Returns True when current volume >= multiplier × recent average."""
    try:
        snapshots = await get_recent_snapshots(market_id, VOLUME_AVERAGE_WINDOW)
        if len(snapshots) < 3:
            return False
        avg = sum(r["volume"] for r in snapshots) / len(snapshots)
        return current_volume >= avg * VOLUME_SPIKE_MULTIPLIER
    except Exception as e:
        print(f"[ERROR] check_volume_spike failed for {market_id}: {e}")
        return False


async def check_strong_signal(market_id: str, current_price: float, current_volume: float) -> tuple[bool, float]:
    """Returns (triggered, signed_change). Triggered when both price AND volume conditions fire."""
    try:
        price_hit, price_change = await check_price_movement(market_id, current_price)
        volume_hit = await check_volume_spike(market_id, current_volume)
        return price_hit and volume_hit, price_change
    except Exception as e:
        print(f"[ERROR] check_strong_signal failed for {market_id}: {e}")
        return False, 0.0
