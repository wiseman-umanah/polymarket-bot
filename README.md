# PolySignal

A Telegram bot that monitors active [Polymarket](https://polymarket.com) prediction markets, detects unusual price and volume activity, and delivers real-time alerts to anyone who subscribes.

---

## How it works

Every 30 seconds the bot fetches the top 100 most-active markets from Polymarket's public API. For each market it stores a snapshot and runs three signal checks:

| Signal | Condition |
|---|---|
| 📈 Price movement | Price shifted ±4%+ compared to 5 minutes ago |
| 📊 Volume spike | Current volume is 2×+ the recent rolling average |
| 🚨 Strong signal | Both conditions fire at the same time |

When a signal fires, the bot broadcasts an alert to every subscriber. Each market has a 15-minute cooldown per signal type to prevent spam.

---

## Alert format

```
🚨 STRONG SIGNAL

Market : Will BTC reach $200k by end of 2026?
Price  : 64.2%
Move   : UP +6.2%
Volume : $1,234,567
Signal : Price moved 4%+ and volume spiked 2×+
Link   : View Market
```

---

## Telegram commands

### For everyone

| Command | Description |
|---|---|
| `/start` | Subscribe to alerts |
| `/stop` | Unsubscribe |
| `/status` | Bot uptime, markets monitored, alerts sent today |
| `/top` | Top 5 markets by price movement right now |
| `/market <term>` | Search for a specific market by name |
| `/history` | Last 5 alerts the bot sent |
| `/thresholds` | Show the global signal detection settings |
| `/mystats` | Your subscription date and current preferences |

### Personal preferences

| Command | Description |
|---|---|
| `/alerts [all\|price\|volume\|strong]` | Filter which signal types you receive |
| `/quiet [HH HH\|off]` | Set a quiet window in UTC (e.g. `/quiet 22 07`) |
| `/minvol [amount\|reset]` | Personal minimum market volume (e.g. `/minvol 50000`) |
| `/pricefilter [value\|reset]` | Personal price move threshold (e.g. `/pricefilter 0.08` or `/pricefilter 8`) |

### Admin only

| Command | Description |
|---|---|
| `/admin` | Pause/Resume button — stops all alerts globally |
| `/adminstats` | Subscriber count, alert stats, mode, failure count |
| `/broadcast <text>` | Push a message to all subscribers |

---

## Local setup

### Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) package manager
- A Telegram bot token from [@BotFather](https://t.me/botfather)

### 1. Install dependencies

```bash
uv sync
```

### 2. Create a Telegram bot

1. Open Telegram and message [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the prompts
3. Copy the token you receive — it looks like `123456789:ABC-DEF...`

### 3. Get your Telegram chat ID (for `ADMIN_CHAT_ID`)

Message [@userinfobot](https://t.me/userinfobot) on Telegram. It will reply with your numeric ID.

### 4. Configure

```bash
cp .env.example .env
```

Open `.env` and fill in at minimum:

```env
TELEGRAM_BOT_TOKEN=your_token_here
ADMIN_CHAT_ID=your_numeric_id_here
```

### 5. Run

```bash
uv run polymarket-bot
```

Or directly:

```bash
uv run python -m bot
```

The bot starts in **polling mode** locally (no webhook needed). It will log to `bot.log` and print status to stdout.

---

## Railway deployment

Railway is the recommended hosting platform. It provides free PostgreSQL and a public HTTPS URL.

### 1. Create a new Railway project

Go to [railway.app](https://railway.app) and create a new empty project.

### 2. Add a PostgreSQL database

In your project dashboard → **New** → **Database** → **PostgreSQL**.
Railway automatically injects `DATABASE_URL` into your service's environment.

### 3. Deploy the bot

Connect your GitHub repository to Railway or push via the Railway CLI:

```bash
railway up
```

### 4. Set environment variables

In Railway → your service → **Variables**, add:

```
TELEGRAM_BOT_TOKEN=your_token_here
ADMIN_CHAT_ID=your_numeric_id_here
```

All other settings have sensible defaults. See [BOT.md](BOT.md) for the full reference.

### 5. Add a webhook URL

Once the service is deployed, Railway gives you a public URL under the **Domains** tab (e.g. `https://polymarket-bot.up.railway.app`).

Add it as an environment variable:

```
WEBHOOK_URL=https://polymarket-bot.up.railway.app
```

Save → Railway restarts the service → the bot switches from polling to webhook mode automatically and registers the URL with Telegram.

---

## Configuration reference

Copy `.env.example` to `.env` and adjust as needed. See [BOT.md](BOT.md) for a detailed explanation of every setting.

| Variable | Default | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | **Required.** Bot token from BotFather |
| `ADMIN_CHAT_ID` | — | **Required.** Your Telegram user ID — grants `/admin` access |
| `DATABASE_URL` | _(empty)_ | PostgreSQL URL — set automatically by Railway; empty = SQLite locally |
| `SQLITE_PATH` | `polymarket.db` | Local SQLite file path (local dev only) |
| `MIN_VOLUME` | `10000` | Minimum total market volume in USD |
| `MIN_VOLUME_24HR` | `1000` | Minimum 24h market volume in USD |
| `MARKET_FETCH_LIMIT` | `100` | Markets fetched per poll cycle |
| `POLL_INTERVAL` | `30` | Seconds between market scans |
| `ALERT_COOLDOWN_MINUTES` | `15` | Per-market, per-signal cooldown |
| `PRICE_CHANGE_THRESHOLD` | `0.04` | Global price move threshold (4%) |
| `VOLUME_SPIKE_MULTIPLIER` | `2.0` | Global volume spike multiplier |
| `VOLUME_AVERAGE_WINDOW` | `10` | Snapshots used to compute volume average |
| `LOOKBACK_MINUTES` | `5` | Minutes back for price comparison |
| `DB_PRUNE_DAYS` | `7` | Days of snapshots to retain |
| `WEBHOOK_URL` | _(empty)_ | Public HTTPS URL — enables webhook mode |
| `PORT` | `8443` | Webhook listener port |
| `WEBHOOK_SECRET` | _(empty)_ | Optional secret token for webhook security |

---

## Project structure

```
bot/
├── config.py          — all settings, loaded from .env
├── state.py           — shared runtime state (paused, uptime, etc.)
├── api.py             — fetches and filters markets from Gamma API
├── detector.py        — price movement and volume spike checks
├── notifier.py        — broadcasts alerts with per-user preference filtering
├── jobs.py            — the market polling job that runs every 30s
├── app.py             — wires everything together, entry point
├── db/
│   ├── core.py        — Database class (PostgreSQL + SQLite dual backend)
│   ├── snapshots.py   — market snapshot queries
│   ├── alerts.py      — alert history queries
│   └── subscribers.py — subscriber and per-user preferences
└── handlers/
    ├── user.py        — user-facing commands
    ├── preferences.py — preference commands (/alerts, /quiet, etc.)
    └── admin.py       — admin-only commands and inline panel
```

---

## Troubleshooting

**Not receiving alerts**
- Send `/start` to the bot — you must subscribe first
- Check `bot.log` for errors
- Temporarily lower `PRICE_CHANGE_THRESHOLD=0.01` to confirm the pipeline works
- Test Telegram connectivity:
  ```bash
  curl -X POST https://api.telegram.org/bot<TOKEN>/sendMessage \
    -d chat_id=<YOUR_ID> -d text="test"
  ```

**Bot started but nothing happens**
- Run `/status` — if it replies, the bot is alive and polling
- Run `/thresholds` to confirm settings are loaded correctly
- Markets need a few poll cycles before signals can fire (the lookback window needs data)

**Webhook not working on Railway**
- Confirm `WEBHOOK_URL` is set to your Railway public domain (no trailing slash)
- Check that the domain is active under the **Domains** tab in Railway
- The bot logs `Webhook mode — port X` on startup if it registered correctly

**Quiet hours not working**
- Hours are in UTC. Use `/mystats` to confirm your saved settings.

---

## License

MIT — free to use, modify, and deploy.
