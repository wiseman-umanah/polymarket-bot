import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Market Filtering Thresholds
MIN_VOLUME = int(os.getenv("MIN_VOLUME", "10000"))
MIN_VOLUME_24HR = int(os.getenv("MIN_VOLUME_24HR", "1000"))

# Polling Configuration
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))
ALERT_COOLDOWN_MINUTES = int(os.getenv("ALERT_COOLDOWN_MINUTES", "15"))

# Signal Detection Thresholds
PRICE_CHANGE_THRESHOLD = float(os.getenv("PRICE_CHANGE_THRESHOLD", "0.04"))
VOLUME_SPIKE_MULTIPLIER = float(os.getenv("VOLUME_SPIKE_MULTIPLIER", "2.0"))
VOLUME_AVERAGE_WINDOW = int(os.getenv("VOLUME_AVERAGE_WINDOW", "10"))
LOOKBACK_MINUTES = int(os.getenv("LOOKBACK_MINUTES", "5"))

# Database Maintenance
DB_PRUNE_DAYS = int(os.getenv("DB_PRUNE_DAYS", "7"))

# API Configuration
MARKET_FETCH_LIMIT = int(os.getenv("MARKET_FETCH_LIMIT", "100"))
GAMMA_API_URL = "https://gamma-api.polymarket.com/markets"
GAMMA_API_PARAMS = {
    "active": "true",
    "closed": "false",
    "order": "volumeNum",
    "ascending": "false",
    "limit": str(MARKET_FETCH_LIMIT),
}

# Database Configuration
DB_PATH = "polymarket.db"

# Telegram API
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
