#!/usr/bin/env bash
# PolySignal VPS Setup — Ubuntu / Debian
# Run as root: sudo bash setup.sh
set -euo pipefail

BOT_DIR="/opt/polymarket-bot"
BOT_USER="polymarket"
SERVICE_NAME="polymarket-bot"

# ── colours ────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── root check ─────────────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && error "Run this script as root: sudo bash setup.sh"

info "Starting PolySignal setup..."

# ── system packages ────────────────────────────────────────────────────────
info "Updating package list..."
apt-get update -qq

info "Installing Python 3 and dependencies..."
apt-get install -y -qq python3 python3-pip python3-venv curl

# ── uv ─────────────────────────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
    info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
else
    info "uv already installed ($(uv --version))"
fi

# ── dedicated user ─────────────────────────────────────────────────────────
if ! id "$BOT_USER" &>/dev/null; then
    info "Creating system user '$BOT_USER'..."
    useradd --system --no-create-home --shell /bin/false "$BOT_USER"
else
    info "User '$BOT_USER' already exists"
fi

# ── copy bot files ─────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(dirname "$SCRIPT_DIR")"

info "Copying bot files to $BOT_DIR..."
mkdir -p "$BOT_DIR"
rsync -a --exclude='.git' --exclude='.venv' --exclude='__pycache__' \
    --exclude='*.pyc' --exclude='polymarket.db' --exclude='bot.log' \
    "$SOURCE_DIR/" "$BOT_DIR/"

# ── python environment ─────────────────────────────────────────────────────
info "Creating Python virtual environment..."
cd "$BOT_DIR"
uv venv .venv
uv sync

# ── environment config ─────────────────────────────────────────────────────
if [[ ! -f "$BOT_DIR/.env" ]]; then
    cp "$BOT_DIR/.env.example" "$BOT_DIR/.env"
    warn "Created $BOT_DIR/.env from example."
    warn "Edit it now with your Telegram credentials before starting the bot:"
    warn "  sudo nano $BOT_DIR/.env"
else
    info ".env already exists — skipping"
fi

# ── permissions ────────────────────────────────────────────────────────────
info "Setting file permissions..."
chown -R "$BOT_USER:$BOT_USER" "$BOT_DIR"
chmod 600 "$BOT_DIR/.env"

# ── systemd service ────────────────────────────────────────────────────────
info "Installing systemd service..."
cp "$BOT_DIR/deploy/polymarket-bot.service" "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

# ── logrotate ──────────────────────────────────────────────────────────────
info "Installing logrotate config..."
cp "$BOT_DIR/deploy/logrotate.conf" "/etc/logrotate.d/$SERVICE_NAME"

# ── summary ────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  PolySignal installed successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Next steps:"
echo ""
echo "  1. Add your Telegram credentials:"
echo "       sudo nano $BOT_DIR/.env"
echo ""
echo "  2. Start the bot:"
echo "       sudo systemctl start $SERVICE_NAME"
echo ""
echo "  3. Check it's running:"
echo "       sudo systemctl status $SERVICE_NAME"
echo ""
echo "  4. Watch live logs:"
echo "       sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "  Useful commands:"
echo "    Stop:    sudo systemctl stop $SERVICE_NAME"
echo "    Restart: sudo systemctl restart $SERVICE_NAME"
echo "    Logs:    tail -f $BOT_DIR/bot.log"
echo ""
