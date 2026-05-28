What the bot connects to

TELEGRAM_BOT_TOKEN — the bot's identity/password on Telegram. Every message it sends uses this.
TELEGRAM_CHAT_ID — your personal Telegram ID. The bot only sends alerts to you, no one else.

Which markets it watches

MIN_VOLUME=10000 — ignores any market with less than $10,000 total traded. Filters out dead/illiquid markets nobody is betting on.
MIN_VOLUME_24HR=1000 — also ignores markets that haven't seen at least $1,000 traded in the last 24 hours. Keeps the focus on markets with recent activity.
MARKET_FETCH_LIMIT=100 — checks the top 100 most active Polymarket markets every cycle.

How often it checks

POLL_INTERVAL=30 — scans all 100 markets every 30 seconds.

What triggers an alert

PRICE_CHANGE_THRESHOLD=0.04 — fires a price alert if the probability on a market moves 4% or more within 5 minutes. A market going from 60% → 64% in 5 minutes would trigger this.
VOLUME_SPIKE_MULTIPLIER=2.0 — fires a volume alert if the current trading volume is 2× higher than the recent average. Sudden bursts of betting activity get caught here.
VOLUME_AVERAGE_WINDOW=10 — the "recent average" above is calculated using the last 10 snapshots (i.e. the last ~5 minutes of data).
LOOKBACK_MINUTES=5 — price movement is measured by comparing the current price against what it was exactly 5 minutes ago.

Spam prevention

ALERT_COOLDOWN_MINUTES=15 — once an alert fires for a market, that same market won't trigger the same alert again for 15 minutes. Prevents getting 30 identical messages in a row.

Housekeeping

DB_PRUNE_DAYS=7 — the bot stores historical price/volume snapshots in a local database. Anything older than 7 days gets deleted automatically to keep the file small.

