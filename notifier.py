import requests
from config import TELEGRAM_API_URL, TELEGRAM_CHAT_ID


def send_alert(market_name, market_id, signal_type, price, volume, slug):
    """
    Send alert to Telegram with formatted message.
    
    Args:
        market_name: Name of the market
        market_id: Market identifier
        signal_type: Type of signal ("price", "volume", "strong")
        price: Current price (0.0 to 1.0)
        volume: Current volume in USD
        slug: Market slug for URL
    """
    try:
        # Determine emoji and signal description
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

        # Format message
        message = f"""{emoji} {title}

Market: {market_name}
Price:  {price:.2%}
Volume: ${volume:,.0f}
Signal: {description}
Link:   https://polymarket.com/market/{slug}"""

        # Send to Telegram
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }

        response = requests.post(TELEGRAM_API_URL, json=payload, timeout=10)
        response.raise_for_status()

        print(f"[ALERT] Sent {signal_type} alert for {market_name}")

    except requests.RequestException as e:
        print(f"[ERROR] Failed to send Telegram alert: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected error in send_alert: {e}")
