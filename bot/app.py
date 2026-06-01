import asyncio
import logging
import signal
from telegram import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from bot.config import (
    TELEGRAM_BOT_TOKEN, ADMIN_CHAT_ID, POLL_INTERVAL,
    WEBHOOK_URL, PORT, HEALTH_PORT, WEBHOOK_SECRET,
)
from bot.state import state
from bot.db import init_db
from bot.api import fetch_markets
from bot.notifier import broadcast_message
from bot.jobs import poll_markets
from bot.handlers.user import (
    cmd_start, cmd_stop, cmd_help, cmd_unknown, cmd_status, cmd_thresholds,
    cmd_top, cmd_market, cmd_history, cmd_mystats,
)
from bot.handlers.preferences import cmd_alerts, cmd_quiet, cmd_minvol, cmd_pricefilter
from bot.handlers.admin import cmd_admin, cmd_adminstats, cmd_broadcast, admin_callback

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(),
    ],
)


def _build_app() -> Application:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("thresholds", cmd_thresholds))
    app.add_handler(CommandHandler("top", cmd_top))
    app.add_handler(CommandHandler("market", cmd_market))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("mystats", cmd_mystats))
    app.add_handler(CommandHandler("alerts", cmd_alerts))
    app.add_handler(CommandHandler("quiet", cmd_quiet))
    app.add_handler(CommandHandler("minvol", cmd_minvol))
    app.add_handler(CommandHandler("pricefilter", cmd_pricefilter))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("adminstats", cmd_adminstats))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))

    # Must be last — catches any command not matched above
    app.add_handler(MessageHandler(filters.COMMAND, cmd_unknown))

    app.job_queue.run_repeating(poll_markets, interval=POLL_INTERVAL, first=15)

    return app


_USER_COMMANDS = [
    BotCommand("start",       "Subscribe to alerts"),
    BotCommand("stop",        "Unsubscribe from alerts"),
    BotCommand("help",        "Show available commands"),
    BotCommand("status",      "Bot uptime and stats"),
    BotCommand("top",         "Top 5 movers right now"),
    BotCommand("market",      "Search for a market by name"),
    BotCommand("history",     "Last 5 alerts sent"),
    BotCommand("thresholds",  "Global signal detection settings"),
    BotCommand("alerts",      "Set your signal filter (all/price/volume/strong)"),
    BotCommand("quiet",       "Set quiet hours (e.g. /quiet 22 07)"),
    BotCommand("minvol",      "Set personal min volume (e.g. /minvol 50000)"),
    BotCommand("pricefilter", "Set personal price threshold (e.g. /pricefilter 8)"),
    BotCommand("mystats",     "View your current settings"),
]

_ADMIN_COMMANDS = _USER_COMMANDS + [
    BotCommand("admin",      "Pause / resume all alerts"),
    BotCommand("adminstats", "Subscriber count and bot stats"),
    BotCommand("broadcast",  "Send a message to all subscribers"),
]


async def _register_commands(app: Application):
    await app.bot.set_my_commands(_USER_COMMANDS, scope=BotCommandScopeDefault())
    if ADMIN_CHAT_ID:
        await app.bot.set_my_commands(_ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=ADMIN_CHAT_ID))

    await app.bot.set_my_description(
        "PolySignal monitors Polymarket prediction markets and sends real-time alerts "
        "when unusual price or volume activity is detected.\n\n"
        "Send /start to subscribe."
    )
    await app.bot.set_my_short_description("Real-time Polymarket alerts on Telegram")


async def _health_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        await reader.read(4096)
    except Exception:
        pass
    writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nOK")
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def _run():
    await init_db()
    state.start_time = __import__("datetime").datetime.now()

    markets = await asyncio.to_thread(fetch_markets)
    state.last_market_count = len(markets)

    app = _build_app()

    async with app:
        await app.start()

        await _register_commands(app)

        if WEBHOOK_URL:
            await app.updater.start_webhook(
                listen="0.0.0.0",
                port=PORT,
                url_path=TELEGRAM_BOT_TOKEN,
                webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}",
                drop_pending_updates=True,
                secret_token=WEBHOOK_SECRET or None,
            )
            print(f"[INFO] Webhook mode — port {PORT}")
        else:
            await app.updater.start_polling(drop_pending_updates=True)
            print("[INFO] Polling mode")

        health_server = await asyncio.start_server(_health_handler, "0.0.0.0", HEALTH_PORT)
        print(f"[INFO] Health check on port {HEALTH_PORT}")

        msg = f"Bot started. Monitoring {len(markets)} markets."
        await broadcast_message(app.bot, msg)
        print(f"[INFO] {msg}")

        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)

        await stop_event.wait()

        print("[INFO] Shutting down...")
        health_server.close()
        await app.updater.stop()
        await app.stop()


def main():
    print("[INFO] Starting PolySignal")
    asyncio.run(_run())
