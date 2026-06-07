# Bot Settings Reference

A plain-English explanation of every setting in `.env`. All settings are optional except `TELEGRAM_BOT_TOKEN` and `ADMIN_CHAT_ID`.

---

## Required

### `TELEGRAM_BOT_TOKEN`
The bot's identity on Telegram. Get one from [@BotFather](https://t.me/botfather) by sending `/newbot`.

```
TELEGRAM_BOT_TOKEN=123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
```

### `ADMIN_CHAT_ID`
Your personal Telegram numeric ID. Only this account can use `/admin`, `/adminstats`, and `/broadcast`. Get it by messaging [@userinfobot](https://t.me/userinfobot).

```
ADMIN_CHAT_ID=987654321
```

---

## Database

### `DATABASE_URL`
PostgreSQL connection string. **Railway injects this automatically** when you add a PostgreSQL plugin — you don't set it manually. Leave it empty locally to use SQLite.

```
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

When empty, the bot uses a local SQLite file instead. The same codebase handles both — no changes needed.

### `SQLITE_PATH`
Path to the local SQLite database file. Only used when `DATABASE_URL` is empty.

```
SQLITE_PATH=polymarket.db   # default
```

### `DB_PRUNE_DAYS`
Snapshots older than this many days are deleted automatically once per hour. Keeps the database from growing indefinitely.

```
DB_PRUNE_DAYS=7   # default — keeps one week of history
```

---

## Market filtering

These settings control which markets the bot watches. Markets that don't pass both volume filters are ignored entirely.

### `MIN_VOLUME`
Minimum total lifetime volume a market must have to be monitored. Filters out illiquid or brand-new markets that nobody is betting on.

```
MIN_VOLUME=10000   # default — must have $10,000+ traded overall
```

### `MIN_VOLUME_24HR`
Minimum volume traded in the last 24 hours. Filters out markets that were once active but have gone quiet.

```
MIN_VOLUME_24HR=1000   # default — must have $1,000+ traded today
```

### `MARKET_FETCH_LIMIT`
How many markets to fetch per poll cycle, sorted by total volume descending. The bot always monitors the most active markets.

```
MARKET_FETCH_LIMIT=100   # default — top 100 markets
```

---

## Polling

### `POLL_INTERVAL`
How often (in seconds) the bot fetches market data and runs signal checks.

```
POLL_INTERVAL=30   # default — every 30 seconds
```

Lower values give faster alerts but increase API load. 30 seconds is a good balance for Polymarket's update frequency.

---

## Signal detection

These are the **global** thresholds. Individual users can set their own stricter thresholds via bot commands — see the [Per-user preferences](#per-user-preferences) section.

### `PRICE_CHANGE_THRESHOLD`
How much a market's probability must shift to trigger a price alert. Expressed as a decimal (0.04 = 4%).

```
PRICE_CHANGE_THRESHOLD=0.04   # default — 4% move within 5 minutes
```

Example: a market moving from 60% → 64% within 5 minutes would trigger this.

### `VOLUME_SPIKE_MULTIPLIER`
How many times larger than the recent average the current volume must be to trigger a volume alert.

```
VOLUME_SPIKE_MULTIPLIER=2.0   # default — must be 2× the recent average
```

### `VOLUME_AVERAGE_WINDOW`
How many recent snapshots to use when computing the "recent average" for volume spike detection. At 30-second intervals, 10 snapshots covers approximately 5 minutes.

```
VOLUME_AVERAGE_WINDOW=10   # default — average of last 10 snapshots (~5 min)
```

### `LOOKBACK_MINUTES`
How far back to look when comparing the current price to detect movement. The bot finds the most recent snapshot at or before this many minutes ago and computes the change.

```
LOOKBACK_MINUTES=5   # default — compare current price to ~5 minutes ago
```

### `ALERT_COOLDOWN_MINUTES`
Once an alert fires for a market and signal type, that combination is suppressed for this many minutes. This prevents the same market from spamming the same alert repeatedly during a sustained move.

```
ALERT_COOLDOWN_MINUTES=15   # default — 15-minute cooldown per market per signal
```

Each signal type (price, volume, strong) has its own independent cooldown. A market can trigger a volume alert and a price alert in the same window, but not two price alerts within 15 minutes.

---

## Server (webhook / health check)

### `WEBHOOK_URL`
The public HTTPS URL of your Railway deployment. When set, the bot switches from polling to webhook mode — Telegram pushes updates directly to this URL instead of the bot polling for them.

```
WEBHOOK_URL=https://your-bot.up.railway.app
```

Leave empty locally. Set this **after** deploying to Railway and obtaining your public domain from the Domains tab.

### `PORT`
The port the webhook HTTP server listens on. Railway routes external traffic to this port.

```
PORT=8443   # default
```

### `WEBHOOK_SECRET`
An optional random string that Telegram includes in every webhook request as a header. The bot verifies it to reject spoofed requests. Recommended for production.

```
WEBHOOK_SECRET=some_long_random_string_here
```

Generate one with: `python -c "import secrets; print(secrets.token_hex(32))"`

---

## Per-user preferences

These are not `.env` settings — they are controlled by each subscriber directly through Telegram commands. The global thresholds above act as defaults; a user's personal settings override them only for that user.

### `/alerts [all|price|volume|strong]`
Filter which signal types you receive.

| Value | You receive |
|---|---|
| `all` | Price, volume, and strong signals (default) |
| `price` | Price and strong signals |
| `volume` | Volume and strong signals |
| `strong` | Strong signals only (both conditions together) |

### `/quiet <start_hour> <end_hour>`
Suppress all alerts during a time window. Hours are in UTC (0–23).

```
/quiet 22 07     → silent from 22:00 to 07:00 UTC (spans midnight)
/quiet off       → disable quiet hours
```

### `/minvol [amount|reset]`
Raise your personal minimum volume threshold. Useful if you only want alerts on high-liquidity markets.

```
/minvol 50000    → only alert on markets with $50,000+ volume
/minvol reset    → use the global default
```

### `/pricefilter [value|reset]`
Raise your personal price move threshold. Useful if the default 4% generates too many alerts.

```
/pricefilter 0.08   → only alert on 8%+ moves (decimal form)
/pricefilter 8      → same, percentage form
/pricefilter reset  → use the global default
```

Run `/mystats` at any time to see all your current settings.
