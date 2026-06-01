import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# Database — Railway injects DATABASE_URL automatically; empty = SQLite locally
DATABASE_URL = os.getenv("DATABASE_URL", "")
SQLITE_PATH = os.getenv("SQLITE_PATH", "polymarket.db")

# Market filtering
MIN_VOLUME = int(os.getenv("MIN_VOLUME", "10000"))
MIN_VOLUME_24HR = int(os.getenv("MIN_VOLUME_24HR", "1000"))

# Polling
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))
ALERT_COOLDOWN_MINUTES = int(os.getenv("ALERT_COOLDOWN_MINUTES", "15"))

# Signal detection
PRICE_CHANGE_THRESHOLD = float(os.getenv("PRICE_CHANGE_THRESHOLD", "0.04"))
VOLUME_SPIKE_MULTIPLIER = float(os.getenv("VOLUME_SPIKE_MULTIPLIER", "2.0"))
VOLUME_AVERAGE_WINDOW = int(os.getenv("VOLUME_AVERAGE_WINDOW", "10"))
LOOKBACK_MINUTES = int(os.getenv("LOOKBACK_MINUTES", "5"))

# Database maintenance
DB_PRUNE_DAYS = int(os.getenv("DB_PRUNE_DAYS", "7"))

# Gamma API
MARKET_FETCH_LIMIT = int(os.getenv("MARKET_FETCH_LIMIT", "100"))
GAMMA_API_URL = "https://gamma-api.polymarket.com/markets"
GAMMA_API_PARAMS = {
    "active": "true",
    "closed": "false",
    "order": "volumeNum",
    "ascending": "false",
    "limit": str(MARKET_FETCH_LIMIT),
}

# Server — set WEBHOOK_URL on Railway; leave empty to use polling locally
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT = int(os.getenv("PORT", "8443"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
