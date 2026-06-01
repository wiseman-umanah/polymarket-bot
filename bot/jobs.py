import asyncio
import logging
from datetime import datetime, timedelta, timezone
from telegram.ext import ContextTypes
from bot.config import (
    ADMIN_CHAT_ID, POLL_INTERVAL, ALERT_COOLDOWN_MINUTES, DB_PRUNE_DAYS,
)
from bot.state import state
from bot.api import fetch_markets
from bot.detector import check_price_movement, check_volume_spike, check_strong_signal
from bot.notifier import broadcast_alert
from bot.db import (
    insert_snapshot, insert_alert, get_last_alert,
    prune_old_snapshots,
)

logger = logging.getLogger(__name__)

_PRUNE_EVERY_N_CYCLES = max(1, 3600 // POLL_INTERVAL)
_prune_counter = 0


async def _is_on_cooldown(market_id: str, signal_type: str) -> bool:
    try:
        last = await get_last_alert(market_id, signal_type)
        if not last:
            return False
        sent_at = last["sent_at"]
        if isinstance(sent_at, str):
            sent_at = datetime.fromisoformat(sent_at)
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=ALERT_COOLDOWN_MINUTES)
        sent_naive = sent_at.replace(tzinfo=None) if sent_at.tzinfo else sent_at
        return sent_naive > cutoff
    except Exception:
        logger.exception(f"Cooldown check failed for {market_id}")
        return False


async def _notify_admin(bot, text: str):
    try:
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ {text}")
    except Exception:
        pass


async def poll_markets(context: ContextTypes.DEFAULT_TYPE):
    global _prune_counter

    if state.paused:
        return

    try:
        markets = await asyncio.to_thread(fetch_markets)
        state.last_market_count = len(markets)
        state.consecutive_failures = 0
        logger.info(f"Fetched {len(markets)} markets")

        alerts_sent = 0
        for market in markets:
            try:
                mid = market["market_id"]
                name = market["market_name"]
                price = market["price"]
                volume = market["volume"]
                slug = market["slug"]

                await insert_snapshot(mid, name, price, volume, slug)

                strong, price_change = await check_strong_signal(mid, price, volume)
                price_hit, price_change = await check_price_movement(mid, price)
                volume_hit = await check_volume_spike(mid, volume)

                if strong and not await _is_on_cooldown(mid, "strong"):
                    await broadcast_alert(context.bot, name, mid, "strong", price, volume, slug, price_change)
                    await insert_alert(mid, "strong")
                    alerts_sent += 1
                else:
                    if price_hit and not await _is_on_cooldown(mid, "price"):
                        await broadcast_alert(context.bot, name, mid, "price", price, volume, slug, price_change)
                        await insert_alert(mid, "price")
                        alerts_sent += 1
                    if volume_hit and not await _is_on_cooldown(mid, "volume"):
                        await broadcast_alert(context.bot, name, mid, "volume", price, volume, slug, price_change)
                        await insert_alert(mid, "volume")
                        alerts_sent += 1

            except Exception:
                logger.exception(f"Failed to process market {market.get('market_id')}")

        logger.info(f"Cycle complete: {alerts_sent} alert(s)" if alerts_sent else "Cycle complete: no signals")

    except Exception as e:
        state.consecutive_failures += 1
        logger.exception("poll_markets failed")
        if state.consecutive_failures >= 3:
            await _notify_admin(
                context.bot,
                f"Market polling failed {state.consecutive_failures}× in a row.\nLast error: {e}",
            )

    _prune_counter += 1
    if _prune_counter >= _PRUNE_EVERY_N_CYCLES:
        deleted = await prune_old_snapshots(DB_PRUNE_DAYS)
        if deleted:
            logger.info(f"Pruned {deleted} old snapshots")
        _prune_counter = 0
