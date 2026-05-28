from db import (
    get_snapshot_5min_ago,
    get_recent_snapshots,
)
from config import PRICE_CHANGE_THRESHOLD, VOLUME_SPIKE_MULTIPLIER, VOLUME_AVERAGE_WINDOW


def check_price_movement(market_id, current_price):
    """
    Check if price has moved 4% or more within ~5 minutes.

    Args:
        market_id: Market identifier
        current_price: Current price (0.0 to 1.0)

    Returns:
        Tuple of (triggered: bool, signed_change: float)
    """
    try:
        old_snapshot = get_snapshot_5min_ago(market_id)

        if not old_snapshot:
            return False, 0.0

        old_price = old_snapshot["price"]
        signed_change = current_price - old_price

        return abs(signed_change) >= PRICE_CHANGE_THRESHOLD, signed_change

    except Exception as e:
        print(f"[ERROR] check_price_movement failed for {market_id}: {e}")
        return False, 0.0


def check_volume_spike(market_id, current_volume):
    """
    Check if volume is 2x or more than recent average.
    
    Args:
        market_id: Market identifier
        current_volume: Current volume in USD
    
    Returns:
        True if volume spike detected, False otherwise
    """
    try:
        recent_snapshots = get_recent_snapshots(market_id, VOLUME_AVERAGE_WINDOW)
        
        if len(recent_snapshots) < 3:
            return False
        
        # Calculate average volume from recent snapshots (excluding current)
        volumes = [row["volume"] for row in recent_snapshots]
        average_volume = sum(volumes) / len(volumes)
        
        return current_volume >= average_volume * VOLUME_SPIKE_MULTIPLIER
    
    except Exception as e:
        print(f"[ERROR] check_volume_spike failed for {market_id}: {e}")
        return False


def check_strong_signal(market_id, current_price, current_volume):
    """
    Check if both price movement AND volume spike are happening.

    Args:
        market_id: Market identifier
        current_price: Current price (0.0 to 1.0)
        current_volume: Current volume in USD

    Returns:
        Tuple of (triggered: bool, signed_change: float)
    """
    try:
        price_movement, price_change = check_price_movement(market_id, current_price)
        volume_spike = check_volume_spike(market_id, current_volume)

        return price_movement and volume_spike, price_change

    except Exception as e:
        print(f"[ERROR] check_strong_signal failed for {market_id}: {e}")
        return False, 0.0
