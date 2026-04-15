import time
import requests
from datetime import datetime
from db import init_db, insert_snapshot, insert_alert, get_last_alert
from api import fetch_markets
from detector import (
    check_price_movement,
    check_volume_spike,
    check_strong_signal,
)
from notifier import send_alert
from config import POLL_INTERVAL, ALERT_COOLDOWN_MINUTES, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def is_on_cooldown(market_id, signal_type):
    """Check if alert is on cooldown (within 15 minutes)."""
    try:
        last_alert = get_last_alert(market_id, signal_type)
        
        if not last_alert:
            return False
        
        # Parse the sent_at timestamp and check if within cooldown
        from datetime import datetime, timedelta
        
        sent_at_str = last_alert["sent_at"]
        sent_at = datetime.fromisoformat(sent_at_str)
        cooldown_threshold = datetime.now() - timedelta(minutes=ALERT_COOLDOWN_MINUTES)
        
        return sent_at > cooldown_threshold
    
    except Exception as e:
        print(f"[ERROR] is_on_cooldown check failed: {e}")
        return False


def handle_telegram_commands():
    """Check for /start command and respond."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if not data.get("ok") or not data.get("result"):
            return

        updates = data.get("result", [])
        
        for update in updates:
            message = update.get("message", {})
            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")

            if text == "/start" and chat_id == int(TELEGRAM_CHAT_ID):
                welcome_message = """👋 Welcome to PolySignal!

I'm monitoring Polymarket for unusual activity.

I'll send you alerts when:
📈 Price moves ≥4% in ~5 minutes
📊 Volume spikes ≥2x average
🚨 Both happen together (strong signal)

Each signal has a 15-min cooldown to avoid spam.

Sit back and watch for alerts! 🚀"""

                payload = {
                    "chat_id": chat_id,
                    "text": welcome_message,
                }
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json=payload,
                    timeout=10,
                )
                print(f"[INFO] Responded to /start command")

                # Delete the update so we don't process it again
                requests.get(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
                    params={"offset": update.get("update_id") + 1},
                    timeout=5,
                )

    except Exception as e:
        print(f"[WARNING] Failed to handle Telegram commands: {e}")


def main():
    """Main polling loop."""
    print("[INFO] Starting Polymarket monitoring bot")
    init_db()
    print("[INFO] Database initialized")
    
    while True:
        try:
            # Check for /start command
            handle_telegram_commands()
            
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Fetch markets
            markets = fetch_markets()
            print(f"[{now}] Fetched {len(markets)} markets")
            
            alerts_sent = 0
            
            for market in markets:
                try:
                    market_id = market["market_id"]
                    market_name = market["market_name"]
                    current_price = market["price"]
                    current_volume = market["volume"]
                    slug = market["slug"]
                    
                    # Insert snapshot
                    insert_snapshot(market_id, market_name, current_price, current_volume)
                    
                    # Check for signals
                    price_signal = check_price_movement(market_id, current_price)
                    volume_signal = check_volume_spike(market_id, current_volume)
                    strong_signal = check_strong_signal(market_id, current_price, current_volume)
                    
                    # Send alerts based on cooldown
                    if strong_signal and not is_on_cooldown(market_id, "strong"):
                        send_alert(market_name, market_id, "strong", current_price, current_volume, slug)
                        insert_alert(market_id, "strong")
                        alerts_sent += 1
                    else:
                        # If no strong signal, check individual signals
                        if price_signal and not is_on_cooldown(market_id, "price"):
                            send_alert(market_name, market_id, "price", current_price, current_volume, slug)
                            insert_alert(market_id, "price")
                            alerts_sent += 1
                        
                        if volume_signal and not is_on_cooldown(market_id, "volume"):
                            send_alert(market_name, market_id, "volume", current_price, current_volume, slug)
                            insert_alert(market_id, "volume")
                            alerts_sent += 1
                
                except Exception as e:
                    print(f"[ERROR] Failed to process market {market_id}: {e}")
                    continue
            
            if alerts_sent > 0:
                print(f"[{now}] Sent {alerts_sent} alert(s)")
            
            time.sleep(POLL_INTERVAL)
        
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
