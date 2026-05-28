import time
import logging
import requests
from datetime import datetime, timedelta, timezone

from db import (
    init_db,
    insert_snapshot,
    insert_alert,
    get_last_alert,
    count_alerts_today,
    prune_old_snapshots,
)
from api import fetch_markets
from detector import check_price_movement, check_volume_spike, check_strong_signal
from notifier import send_alert, send_message
from config import (
    POLL_INTERVAL,
    ALERT_COOLDOWN_MINUTES,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    PRICE_CHANGE_THRESHOLD,
    VOLUME_SPIKE_MULTIPLIER,
    LOOKBACK_MINUTES,
    MIN_VOLUME,
    DB_PRUNE_DAYS,
)

logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Shared mutable state — intentionally module-level for simplicity
BOT_STATE = {
    "paused": False,
    "start_time": None,
    "last_market_count": 0,
}

# How often to prune the DB (once per hour regardless of POLL_INTERVAL)
_PRUNE_EVERY_N_CYCLES = max(1, 3600 // POLL_INTERVAL)


# ---------------------------------------------------------------------------
# Cooldown check
# ---------------------------------------------------------------------------

def is_on_cooldown(market_id, signal_type):
    """Return True if an alert for this market+signal was sent within the cooldown window."""
    try:
        last_alert = get_last_alert(market_id, signal_type)

        if not last_alert:
            return False

        sent_at = datetime.fromisoformat(last_alert["sent_at"])
        # Stored timestamps are UTC; compare against UTC now
        cooldown_threshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=ALERT_COOLDOWN_MINUTES)

        return sent_at > cooldown_threshold

    except Exception as e:
        print(f"[ERROR] is_on_cooldown check failed: {e}")
        logger.exception(f"is_on_cooldown failed for {market_id}")
        return False


# ---------------------------------------------------------------------------
# Telegram command helpers
# ---------------------------------------------------------------------------

def _reply(chat_id, text):
    """Send a plain message to a specific chat ID."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
    except Exception as e:
        print(f"[WARNING] Failed to send command reply: {e}")


def _handle_start(chat_id):
    _reply(chat_id, """👋 Welcome to PolySignal!

I'm monitoring Polymarket for unusual activity.

I'll alert you when:
📈 Price moves ≥4% in ~5 minutes
📊 Volume spikes ≥2x recent average
🚨 Both happen together (strong signal)

Commands:
/status      — uptime and today's stats
/thresholds  — current signal settings
/pause       — stop alerts temporarily
/resume      — restart alerts

Each signal has a 15-min cooldown to avoid spam. 🚀""")
    print("[INFO] Responded to /start")


def _handle_status(chat_id):
    uptime = datetime.now() - BOT_STATE["start_time"]
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes = remainder // 60
    alerts_today = count_alerts_today()
    state_str = "⏸ Paused" if BOT_STATE["paused"] else "✅ Running"

    _reply(chat_id, f"""📊 Bot Status

Uptime  : {hours}h {minutes}m
Markets : {BOT_STATE["last_market_count"]} monitored
Alerts  : {alerts_today} sent today
State   : {state_str}""")
    print("[INFO] Responded to /status")


def _handle_pause(chat_id):
    BOT_STATE["paused"] = True
    _reply(chat_id, "⏸ Bot paused. Send /resume to restart alerting.")
    logger.info("Bot paused via Telegram command")
    print("[INFO] Bot paused via /pause command")


def _handle_resume(chat_id):
    BOT_STATE["paused"] = False
    _reply(chat_id, "▶️ Bot resumed. Monitoring markets.")
    logger.info("Bot resumed via Telegram command")
    print("[INFO] Bot resumed via /resume command")


def _handle_thresholds(chat_id):
    _reply(chat_id, f"""⚙️ Current Thresholds

Price change  : {PRICE_CHANGE_THRESHOLD:.0%}+
Volume spike  : {VOLUME_SPIKE_MULTIPLIER:.1f}x average
Lookback      : {LOOKBACK_MINUTES} min
Cooldown      : {ALERT_COOLDOWN_MINUTES} min
Min volume    : ${MIN_VOLUME:,}""")
    print("[INFO] Responded to /thresholds")


# ---------------------------------------------------------------------------
# Command dispatcher
# ---------------------------------------------------------------------------

def handle_telegram_commands(offset=None):
    """
    Fetch and dispatch pending Telegram commands.
    Returns the next offset to use on the following call.
    """
    try:
        params = {"timeout": 0}
        if offset is not None:
            params["offset"] = offset

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        if not data.get("ok") or not data.get("result"):
            return offset

        updates = data["result"]
        if not updates:
            return offset

        next_offset = offset

        for update in updates:
            update_id = update.get("update_id")
            next_offset = update_id + 1  # advance past every update, processed or not

            message = update.get("message", {})
            text = message.get("text", "").strip()
            chat_id = message.get("chat", {}).get("id")

            if not chat_id or chat_id != int(TELEGRAM_CHAT_ID):
                continue

            if text == "/start":
                _handle_start(chat_id)
            elif text == "/status":
                _handle_status(chat_id)
            elif text == "/pause":
                _handle_pause(chat_id)
            elif text == "/resume":
                _handle_resume(chat_id)
            elif text == "/thresholds":
                _handle_thresholds(chat_id)

        return next_offset

    except Exception as e:
        print(f"[WARNING] Failed to handle Telegram commands: {e}")
        return offset


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    print("[INFO] Starting Polymarket monitoring bot")
    init_db()
    print("[INFO] Database initialized")

    BOT_STATE["start_time"] = datetime.now()

    initial_markets = fetch_markets()
    BOT_STATE["last_market_count"] = len(initial_markets)
    startup_text = f"Bot started. Monitoring {len(initial_markets)} markets."
    send_message(startup_text)
    print(f"[INFO] {startup_text}")
    logger.info(startup_text)

    update_offset = None
    prune_counter = 0

    try:
        while True:
            try:
                update_offset = handle_telegram_commands(update_offset)

                if BOT_STATE["paused"]:
                    time.sleep(POLL_INTERVAL)
                    continue

                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                markets = fetch_markets()
                BOT_STATE["last_market_count"] = len(markets)
                print(f"[{now}] Fetched {len(markets)} markets")
                logger.info(f"Fetched {len(markets)} markets")

                alerts_sent = 0
                signals_detected = []

                for market in markets:
                    try:
                        market_id = market["market_id"]
                        market_name = market["market_name"]
                        current_price = market["price"]
                        current_volume = market["volume"]
                        slug = market["slug"]

                        insert_snapshot(market_id, market_name, current_price, current_volume)

                        price_signal, price_change = check_price_movement(market_id, current_price)
                        volume_signal = check_volume_spike(market_id, current_volume)
                        strong_signal, _ = check_strong_signal(market_id, current_price, current_volume)

                        if strong_signal and not is_on_cooldown(market_id, "strong"):
                            send_alert(market_name, market_id, "strong", current_price, current_volume, slug, price_change)
                            insert_alert(market_id, "strong")
                            alerts_sent += 1
                            signals_detected.append(f"strong:{market_name}")
                            logger.info(f"Alert sent: strong signal for '{market_name}' price={current_price:.2%} change={price_change:+.2%}")
                        else:
                            if price_signal and not is_on_cooldown(market_id, "price"):
                                send_alert(market_name, market_id, "price", current_price, current_volume, slug, price_change)
                                insert_alert(market_id, "price")
                                alerts_sent += 1
                                signals_detected.append(f"price:{market_name}")
                                logger.info(f"Alert sent: price signal for '{market_name}' price={current_price:.2%} change={price_change:+.2%}")

                            if volume_signal and not is_on_cooldown(market_id, "volume"):
                                send_alert(market_name, market_id, "volume", current_price, current_volume, slug, price_change)
                                insert_alert(market_id, "volume")
                                alerts_sent += 1
                                signals_detected.append(f"volume:{market_name}")
                                logger.info(f"Alert sent: volume signal for '{market_name}' volume=${current_volume:,.0f}")

                    except Exception as e:
                        print(f"[ERROR] Failed to process market {market_id}: {e}")
                        logger.exception(f"Failed to process market {market_id}")
                        continue

                if alerts_sent > 0:
                    print(f"[{now}] Sent {alerts_sent} alert(s)")
                    logger.info(f"Cycle complete: {alerts_sent} alert(s) — {', '.join(signals_detected)}")
                else:
                    logger.info("Cycle complete: no signals detected")

                # Prune old snapshots once per hour
                prune_counter += 1
                if prune_counter >= _PRUNE_EVERY_N_CYCLES:
                    deleted = prune_old_snapshots(DB_PRUNE_DAYS)
                    if deleted:
                        logger.info(f"Pruned {deleted} snapshots older than {DB_PRUNE_DAYS} days")
                    prune_counter = 0

                time.sleep(POLL_INTERVAL)

            except Exception as e:
                print(f"[ERROR] {e}")
                logger.exception("Unexpected error in polling cycle")
                time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("[INFO] Bot stopped by user")
        logger.info("Bot stopped by user")
        send_message("Bot stopped.")


if __name__ == "__main__":
    main()
