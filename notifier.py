import time
import requests
from config import TELEGRAM_API_URL, TELEGRAM_CHAT_ID

_MAX_RETRIES = 3
_RETRY_DELAY = 2  # seconds between retries


def _post_with_retry(payload):
    """POST to Telegram API with up to 3 retries on failure."""
    last_exc = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = requests.post(TELEGRAM_API_URL, json=payload, timeout=10)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            last_exc = e
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAY)
    raise last_exc


def send_message(text):
    """Send a plain text message to Telegram."""
    try:
        _post_with_retry({"chat_id": TELEGRAM_CHAT_ID, "text": text})
    except Exception as e:
        print(f"[ERROR] Failed to send Telegram message: {e}")


def send_alert(market_name, market_id, signal_type, price, volume, slug, price_change=0.0):
    """
    Send alert to Telegram with formatted message.

    Args:
        market_name: Name of the market
        market_id: Market identifier
        signal_type: Type of signal ("price", "volume", "strong")
        price: Current price (0.0 to 1.0)
        volume: Current volume in USD
        slug: Market slug for URL
        price_change: Signed price change since ~5 minutes ago
    """
    try:
        if signal_type == "strong":
            emoji = "🚨"
            title = "STRONG SIGNAL"
            description = "Both price movement (4%+) and volume spike (2x+) detected"
        elif signal_type == "price":
            emoji = "📈"
            title = "PRICE MOVEMENT"
            description = "Price movement 4%+ within 5 minutes"
        elif signal_type == "volume":
            emoji = "📊"
            title = "VOLUME SPIKE"
            description = "Volume 2x or more than recent average"
        else:
            return

        if price_change >= 0:
            move_str = f"UP +{price_change:.1%}"
        else:
            move_str = f"DOWN {price_change:.1%}"

        message = f"""{emoji} {title}

Market : {market_name}
Price  : {price:.1%}
Move   : {move_str}
Volume : ${volume:,.0f}
Signal : {description}
Link   : https://polymarket.com/market/{slug}"""

        _post_with_retry({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        })

        print(f"[ALERT] Sent {signal_type} alert for {market_name}")

    except requests.RequestException as e:
        print(f"[ERROR] Failed to send Telegram alert after {_MAX_RETRIES} attempts: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected error in send_alert: {e}")
