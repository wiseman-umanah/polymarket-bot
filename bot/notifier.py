import logging
from datetime import datetime, timezone
from telegram import Bot
from telegram.error import TelegramError
from bot.config import MIN_VOLUME, PRICE_CHANGE_THRESHOLD
from bot.db import get_all_subscribers, get_all_subscriber_preferences

logger = logging.getLogger(__name__)


def _signal_matches_filter(signal_type: str, filter_pref: str) -> bool:
    if filter_pref == "strong":
        return signal_type == "strong"
    if filter_pref == "price":
        return signal_type in ("price", "strong")
    if filter_pref == "volume":
        return signal_type in ("volume", "strong")
    return True  # "all"


def _is_quiet_now(quiet_start: int | None, quiet_end: int | None) -> bool:
    if quiet_start is None or quiet_end is None:
        return False
    hour = datetime.now(timezone.utc).hour
    if quiet_start <= quiet_end:
        return quiet_start <= hour < quiet_end
    return hour >= quiet_start or hour < quiet_end  # spans midnight


async def broadcast_message(bot: Bot, text: str):
    """Send plain text to every subscriber — no filtering."""
    for chat_id in await get_all_subscribers():
        try:
            await bot.send_message(chat_id=chat_id, text=text)
        except TelegramError as e:
            logger.warning(f"broadcast_message → {chat_id}: {e}")


async def broadcast_alert(
    bot: Bot,
    market_name: str,
    market_id: str,
    signal_type: str,
    price: float,
    volume: float,
    slug: str,
    price_change: float = 0.0,
):
    """Send formatted alert to subscribers, respecting each user's preferences."""
    if signal_type == "strong":
        emoji, title, desc = "🚨", "STRONG SIGNAL", "Price moved 4%+ and volume spiked 2×+"
    elif signal_type == "price":
        emoji, title, desc = "📈", "PRICE MOVEMENT", "Price moved 4%+ within 5 minutes"
    elif signal_type == "volume":
        emoji, title, desc = "📊", "VOLUME SPIKE", "Volume is 2×+ the recent average"
    else:
        return

    move_str = f"UP +{price_change:.1%}" if price_change >= 0 else f"DOWN {price_change:.1%}"
    message = (
        f"{emoji} <b>{title}</b>\n\n"
        f"Market : {market_name}\n"
        f"Price  : {price:.1%}\n"
        f"Move   : {move_str}\n"
        f"Volume : ${volume:,.0f}\n"
        f"Signal : {desc}\n"
        f'Link   : <a href="https://polymarket.com/market/{slug}">View Market</a>'
    )

    sent = 0
    for sub in await get_all_subscriber_preferences():
        chat_id = sub["chat_id"]
        try:
            if not _signal_matches_filter(signal_type, sub.get("signal_filter", "all")):
                continue
            if _is_quiet_now(sub.get("quiet_start"), sub.get("quiet_end")):
                continue
            if volume < (sub.get("min_volume") or MIN_VOLUME):
                continue
            if signal_type in ("price", "strong"):
                thresh = sub.get("price_threshold") or PRICE_CHANGE_THRESHOLD
                if abs(price_change) < thresh:
                    continue

            await bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
            sent += 1
        except TelegramError as e:
            logger.warning(f"broadcast_alert → {chat_id}: {e}")
        except Exception:
            logger.exception(f"Unexpected error sending alert to {chat_id}")

    logger.info(f"Broadcast {signal_type} '{market_name}' → {sent} subscriber(s)")
