# Polymarket Monitoring Bot

A lightweight, reliable bot that monitors active Polymarket prediction markets, detects unusual activity (price movements and volume spikes), and sends real-time alerts to Telegram.

## Features

- **Market Polling**: Fetches active markets from Polymarket's Gamma API every 30 seconds
- **Smart Filtering**: Filters markets by volume thresholds to focus on active, liquid markets
- **Signal Detection**:
  - 📈 **Price Movement**: Alerts when price changes ≥4% within ~5 minutes
  - 📊 **Volume Spike**: Alerts when volume is ≥2× recent average
  - 🚨 **Strong Signal**: Alerts when both conditions occur simultaneously
- **Alert Cooldown**: 15-minute cooldown per market per signal type to prevent spam
- **Persistent Storage**: SQLite database tracks market snapshots and alert history
- **Error Handling**: Robust error handling ensures the bot continues running even if API calls fail

## Tech Stack

- **Language**: Python 3.11+
- **HTTP Client**: requests
- **Configuration**: python-dotenv
- **Database**: SQLite 3 (stdlib)
- **Notifications**: Telegram Bot API (raw HTTP)

## Prerequisites

- Python 3.11 or higher
- `uv` package manager
- Telegram Bot Token (get one from [@BotFather](https://t.me/botfather))
- Telegram Chat ID (see setup instructions below)

## Installation

### 1. Clone or Download the Repository

```bash
cd polymarket-bot
```

### 2. Install Dependencies

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync
```

Or if you already have the environment set up:

```bash
uv install
```

### 3. Set Up Telegram

#### Get Your Telegram Bot Token

1. Open Telegram and chat with [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the instructions
3. Copy the API token you receive (format: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

#### Get Your Chat ID

1. Send a message to your bot in Telegram
2. Visit: `https://api.telegram.org/bot{YOUR_BOT_TOKEN}/getUpdates`
3. Replace `{YOUR_BOT_TOKEN}` with your actual token
4. Look for the `"id"` field in the JSON response (your chat ID)

Alternatively, use the [@userinfobot](https://t.me/userinfobot) on Telegram to get your user ID.

### 4. Configure Environment Variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your Telegram credentials and thresholds:

```
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
MIN_VOLUME=10000
MIN_VOLUME_24HR=1000
POLL_INTERVAL=30
ALERT_COOLDOWN_MINUTES=15
PRICE_CHANGE_THRESHOLD=0.04
VOLUME_SPIKE_MULTIPLIER=2.0
VOLUME_AVERAGE_WINDOW=10
LOOKBACK_MINUTES=5
```

### Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | Required |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID | Required |
| `MIN_VOLUME` | Minimum market volume to monitor (USD) | 10,000 |
| `MIN_VOLUME_24HR` | Minimum 24h volume for filtering | 1,000 |
| `POLL_INTERVAL` | Polling frequency (seconds) | 30 |
| `ALERT_COOLDOWN_MINUTES` | Cooldown between alerts per signal | 15 |
| `PRICE_CHANGE_THRESHOLD` | Price change threshold (decimal) | 0.04 (4%) |
| `VOLUME_SPIKE_MULTIPLIER` | Volume spike multiplier | 2.0 (2x average) |
| `VOLUME_AVERAGE_WINDOW` | Number of snapshots for average | 10 |
| `LOOKBACK_MINUTES` | Minutes back for price comparison | 5 |

## Running the Bot

### Local Development

```bash
source .venv/bin/activate  # Activate environment
python main.py
```

The bot will start polling and print logs to the console:

```
[INFO] Starting Polymarket monitoring bot
[INFO] Database initialized
[2026-04-15 10:30:45] Fetched 32 markets
[2026-04-15 10:31:15] Fetched 30 markets
[ALERT] Sent price alert for Will AI Pass the Turing Test by 2030?
```

### Testing

Before running continuously, test your Telegram setup:

1. Start the bot: `python main.py`
2. Wait for it to fetch markets
3. Look for alerts in Telegram when signals are detected
4. Stop the bot with `Ctrl+C`

## Deployment on VPS

### Using `nohup`

```bash
# Install dependencies
uv install

# Start bot in background
nohup python main.py > polymarket-bot.log 2>&1 &

# View logs
tail -f polymarket-bot.log

# Stop bot (get PID from logs or ps)
kill <PID>
```

### Using `systemd` (Recommended)

Create `/etc/systemd/system/polymarket-bot.service`:

```ini
[Unit]
Description=Polymarket Monitoring Bot
After=network.target

[Service]
Type=simple
User=polymarket
WorkingDirectory=/home/polymarket/polymarket-bot
Environment="PATH=/home/polymarket/polymarket-bot/.venv/bin"
ExecStart=/usr/bin/python3 /home/polymarket/polymarket-bot/main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable polymarket-bot
sudo systemctl start polymarket-bot
sudo systemctl status polymarket-bot

# View logs
sudo journalctl -u polymarket-bot -f
```

## Database

The bot stores data in `polymarket.db` (SQLite):

### Snapshots Table
Records market state at each polling interval:
- `market_id`: Polymarket market ID
- `market_name`: Market question/title
- `price`: YES outcome price (0.0-1.0)
- `volume`: 24h volume in USD
- `timestamp`: When the snapshot was taken

### Alerts Table
Records alerts sent:
- `market_id`: Market ID
- `signal_type`: "price", "volume", or "strong"
- `sent_at`: When the alert was sent

## Alert Examples

### Price Movement Alert
```
📈 PRICE MOVEMENT

Market: Will BTC reach $100k by end of 2026?
Price:  75.43%
Volume: $125,340
Signal: Price movement 4%+ within 5 minutes
Link:   https://polymarket.com/market/will-btc-reach-100k-by-end-of-2026
```

### Volume Spike Alert
```
📊 VOLUME SPIKE

Market: Will AI Pass the Turing Test by 2030?
Price:  62.15%
Volume: $287,650
Signal: Volume 2x or more than recent average
Link:   https://polymarket.com/market/will-ai-pass-turing-test-by-2030
```

### Strong Signal Alert
```
🚨 STRONG SIGNAL

Market: Will Trump be elected in 2026?
Price:  58.90%
Volume: $512,000
Signal: Both price movement (4%+) and volume spike (2x+) detected
Link:   https://polymarket.com/market/will-trump-be-elected-2026
```

## Monitoring & Maintenance

### Check Bot Status
```bash
ps aux | grep main.py
```

### View Recent Alerts
```bash
tail -50 polymarket-bot.log
```

### Monitor Database Growth
```bash
ls -lh polymarket.db
```

Snapshots accumulate over time. The database typically grows to 1-5 MB per month of continuous operation.

### Clean Old Data (Optional)

To keep the database lean, periodically delete snapshots older than 30 days:

```python
# In Python REPL or script
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('polymarket.db')
cursor = conn.cursor()

cutoff = datetime.now() - timedelta(days=30)
cursor.execute("DELETE FROM snapshots WHERE timestamp < ?", (cutoff,))
conn.commit()
conn.close()

print(f"Deleted snapshots before {cutoff}")
```

## Troubleshooting

### Bot Not Receiving Alerts

1. **Check Telegram credentials**:
   - Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
   - Test with `curl`:
     ```bash
     curl -X POST https://api.telegram.org/bot{TOKEN}/sendMessage \
       -d chat_id={CHAT_ID} \
       -d text="Test message"
     ```

2. **Check market filtering**:
   - Lower `MIN_VOLUME` or `MIN_VOLUME_24HR` to capture more markets
   - Verify Gamma API is responding: `curl https://gamma-api.polymarket.com/markets?limit=1`

3. **Check signal thresholds**:
   - Lower `PRICE_CHANGE_THRESHOLD` (0.04 = 4%) to catch smaller movements
   - Increase `VOLUME_AVERAGE_WINDOW` for smoother volume calculations

### Bot Crashes or Stops

1. Check logs for errors:
   ```bash
   tail -100 polymarket-bot.log
   ```

2. Verify internet connectivity and API availability

3. Restart the bot:
   ```bash
   pkill -f "python main.py"
   python main.py &
   ```

### High CPU/Memory Usage

- Database queries may slow down if snapshots exceed 1M+ rows
- Clean old data as shown in "Maintenance" section above
- Reduce `VOLUME_AVERAGE_WINDOW` if queries are slow

## License

MIT

## Contributing

This is a simple MVP. Contributions for bug fixes and reliability improvements are welcome.

## Disclaimer

This bot is for monitoring purposes only. Use at your own risk. Polymarket prices and events are subject to market dynamics and may change rapidly.
