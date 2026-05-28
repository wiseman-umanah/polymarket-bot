# PolySignal — Polymarket Monitoring Bot

A lightweight, production-ready bot that monitors active Polymarket prediction markets, detects unusual activity, and delivers real-time alerts straight to Telegram.

---

## Features

| Feature | Details |
|---------|---------|
| 📈 Price movement alerts | Fires when price moves ≥4% within ~5 minutes |
| 📊 Volume spike alerts | Fires when volume is ≥2× the recent average |
| 🚨 Strong signal alerts | Fires when both conditions occur together |
| ⏱ 15-min cooldown | One alert per market per signal type — no spam |
| 💬 Telegram commands | `/status`, `/pause`, `/resume`, `/thresholds` |
| 🗄 Persistent SQLite storage | Survives restarts — history and cooldowns intact |
| 🧹 Automatic DB pruning | Removes snapshots older than 7 days automatically |
| 📝 File logging | Full log written to `bot.log` |
| 🔁 Auto-restart | systemd keeps the bot running 24/7 |

---

## Alert Format

```
🚨 STRONG SIGNAL

Market : Will BTC reach $200k by end of 2026?
Price  : 64.2%
Move   : UP +6.2%
Volume : $1,234,567
Signal : Both price movement (4%+) and volume spike (2x+) detected
Link   : https://polymarket.com/market/will-btc-reach-200k-2026
```

---

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and feature overview |
| `/status` | Uptime, markets monitored, alerts sent today |
| `/pause` | Stop sending alerts (bot keeps running) |
| `/resume` | Resume alerts after a pause |
| `/thresholds` | Show current signal detection settings |

---

## Requirements

- Python 3.11+
- `uv` package manager
- A Telegram bot token (from [@BotFather](https://t.me/botfather))
- Your Telegram chat ID

---

## Local Setup

### 1. Install dependencies

```bash
uv venv
uv sync
```

### 2. Create your Telegram bot

1. Open Telegram and message [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the prompts
3. Copy the token you receive (format: `123456:ABC-DEF...`)

### 3. Get your Telegram chat ID

1. Send any message to your new bot
2. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find the `"id"` field inside `"chat"` in the response

Alternatively, message [@userinfobot](https://t.me/userinfobot) on Telegram.

### 4. Configure

```bash
cp .env.example .env
# Edit .env and fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
```

### 5. Run

```bash
source .venv/bin/activate
python main.py
```

---

## VPS Deployment (Ubuntu / Debian)

### Automated setup

Copy the project to your VPS, then run the setup script as root:

```bash
sudo bash deploy/setup.sh
```

The script will:
- Install Python 3 and `uv`
- Create a dedicated `polymarket` system user
- Copy the bot to `/opt/polymarket-bot`
- Set up the Python virtual environment
- Create `/opt/polymarket-bot/.env` from the example
- Install and enable the systemd service
- Install the logrotate config

After setup, add your Telegram credentials:

```bash
sudo nano /opt/polymarket-bot/.env
```

Then start the bot:

```bash
sudo systemctl start polymarket-bot
sudo systemctl status polymarket-bot
```

### Manual systemd setup

If you prefer to configure manually:

```bash
# Copy the service file
sudo cp deploy/polymarket-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable polymarket-bot
sudo systemctl start polymarket-bot
```

### Useful commands

```bash
# View live logs
sudo journalctl -u polymarket-bot -f

# View file log
tail -f /opt/polymarket-bot/bot.log

# Restart after config change
sudo systemctl restart polymarket-bot

# Stop the bot
sudo systemctl stop polymarket-bot
```

---

## Configuration Reference

Edit `.env` to customise behaviour. All settings have sensible defaults.

See [BOT.md](BOT.md) for a detailed explanation of each setting.

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | **Required.** Your Telegram bot token |
| `TELEGRAM_CHAT_ID` | — | **Required.** Your Telegram user/chat ID |
| `MIN_VOLUME` | `10000` | Minimum total market volume (USD) |
| `MIN_VOLUME_24HR` | `1000` | Minimum 24h market volume (USD) |
| `MARKET_FETCH_LIMIT` | `100` | Markets fetched per poll cycle |
| `PRICE_CHANGE_THRESHOLD` | `0.04` | Price move threshold (0.04 = 4%) |
| `VOLUME_SPIKE_MULTIPLIER` | `2.0` | Volume multiplier to trigger spike alert |
| `VOLUME_AVERAGE_WINDOW` | `10` | Snapshots used to compute volume average |
| `LOOKBACK_MINUTES` | `5` | Minutes back for price comparison |
| `POLL_INTERVAL` | `30` | Seconds between market polls |
| `ALERT_COOLDOWN_MINUTES` | `15` | Cooldown per market per signal type |
| `DB_PRUNE_DAYS` | `7` | Days of snapshots to retain |

---

## Running Tests

```bash
uv run pytest tests/ -v
```

All 58 tests should pass.

---

## Troubleshooting

### Not receiving alerts

1. Verify Telegram credentials in `.env`
2. Test the connection manually:
   ```bash
   curl -X POST https://api.telegram.org/bot<TOKEN>/sendMessage \
     -d chat_id=<CHAT_ID> -d text="test"
   ```
3. Lower thresholds temporarily (`PRICE_CHANGE_THRESHOLD=0.01`) to confirm the pipeline works
4. Check `bot.log` for errors

### Bot keeps stopping

```bash
# Check service status
sudo systemctl status polymarket-bot

# Check logs for crash reason
sudo journalctl -u polymarket-bot --since "10 minutes ago"
```

### Database is growing large

The bot prunes snapshots older than `DB_PRUNE_DAYS` (default 7) automatically. To adjust:

```
DB_PRUNE_DAYS=3  # keep only 3 days
```

Check current DB size:

```bash
ls -lh /opt/polymarket-bot/polymarket.db
```

### Alerts fire at the wrong time

Ensure the VPS is set to UTC:

```bash
timedatectl set-timezone UTC
```

---

## Architecture

```
main.py          — polling loop, Telegram commands, orchestration
api.py           — fetches and filters markets from Gamma API
detector.py      — price movement and volume spike detection
notifier.py      — formats and sends Telegram alerts (with retry)
db.py            — SQLite storage (snapshots, alerts, pruning)
config.py        — all settings loaded from .env
```

---

## License

MIT — free to use, modify, and sell.
