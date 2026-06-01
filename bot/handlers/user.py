from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from bot.config import (
    MIN_VOLUME, PRICE_CHANGE_THRESHOLD, ALERT_COOLDOWN_MINUTES,
    LOOKBACK_MINUTES, VOLUME_SPIKE_MULTIPLIER, ADMIN_CHAT_ID,
)
from bot.state import state
from bot.db import (
    add_subscriber, remove_subscriber, count_subscribers,
    count_alerts_today, get_subscriber_info, get_preferences,
    get_top_movers, search_market_snapshot, get_recent_alerts,
)


def _fmt_ts(ts) -> str:
    if hasattr(ts, "strftime"):
        return ts.strftime("%m-%d %H:%M UTC")
    return str(ts)[:16]


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await add_subscriber(chat_id, update.effective_user.username)
    await update.message.reply_text(
        "👋 <b>Welcome to PolySignal!</b>\n\n"
        "You're subscribed to Polymarket alerts.\n\n"
        "Alerts fire when:\n"
        "📈 Price moves ≥4% within ~5 minutes\n"
        "📊 Volume spikes ≥2× the recent average\n"
        "🚨 Both happen together (strong signal)\n\n"
        "<b>Info:</b>\n"
        "/status      — bot status\n"
        "/top         — top movers right now\n"
        "/market      — look up a market\n"
        "/history     — recent alerts\n"
        "/thresholds  — global signal settings\n\n"
        "<b>Your preferences:</b>\n"
        "/alerts      — set signal filter\n"
        "/quiet       — set quiet hours\n"
        "/minvol      — set min volume\n"
        "/pricefilter — set price move threshold\n"
        "/mystats     — view your settings\n\n"
        "/stop — unsubscribe",
        parse_mode="HTML",
    )


async def cmd_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Unknown command: <code>{update.message.text.split()[0]}</code>\n"
        "Send /help to see everything available.",
        parse_mode="HTML",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    is_admin = chat_id == ADMIN_CHAT_ID

    text = (
        "📖 <b>PolySignal Commands</b>\n\n"
        "<b>General</b>\n"
        "/start         — subscribe to alerts\n"
        "/stop          — unsubscribe\n"
        "/status        — uptime, markets, alerts sent today\n"
        "/top           — top 5 movers right now\n"
        "/market &lt;term&gt; — search markets by name\n"
        "/history       — last 5 alerts sent\n"
        "/thresholds    — global signal settings\n\n"
        "<b>Your preferences</b>\n"
        "/alerts        — filter by signal type (all/price/volume/strong)\n"
        "/quiet         — set quiet hours (e.g. /quiet 22 07)\n"
        "/minvol        — personal min volume (e.g. /minvol 50000)\n"
        "/pricefilter   — personal price threshold (e.g. /pricefilter 8)\n"
        "/mystats       — view all your current settings\n"
    )

    if is_admin:
        text += (
            "\n<b>Admin only</b>\n"
            "/admin         — pause/resume all alerts (inline button)\n"
            "/adminstats    — subscriber count, stats, mode\n"
            "/broadcast &lt;text&gt; — push a message to all subscribers\n"
        )

    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await remove_subscriber(update.effective_chat.id)
    await update.message.reply_text("👋 Unsubscribed. Send /start anytime to resubscribe.")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = datetime.now() - state.start_time
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m = rem // 60
    await update.message.reply_text(
        f"📊 <b>Bot Status</b>\n\n"
        f"Uptime      : {h}h {m}m\n"
        f"Markets     : {state.last_market_count} monitored\n"
        f"Subscribers : {await count_subscribers()}\n"
        f"Alerts today: {await count_alerts_today()}\n"
        f"State       : {'⏸ Paused' if state.paused else '✅ Running'}",
        parse_mode="HTML",
    )


async def cmd_thresholds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"⚙️ <b>Global Thresholds</b>\n\n"
        f"Price change : {PRICE_CHANGE_THRESHOLD:.0%}+\n"
        f"Volume spike : {VOLUME_SPIKE_MULTIPLIER:.1f}× average\n"
        f"Lookback     : {LOOKBACK_MINUTES} min\n"
        f"Cooldown     : {ALERT_COOLDOWN_MINUTES} min\n"
        f"Min volume   : ${MIN_VOLUME:,}",
        parse_mode="HTML",
    )


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    movers = await get_top_movers(5)
    if not movers:
        await update.message.reply_text("No movement data yet — check back after a couple of poll cycles.")
        return
    lines = ["📈 <b>Top Movers (last 5 min)</b>\n"]
    for i, m in enumerate(movers, 1):
        arrow = "▲" if m["price_change"] >= 0 else "▼"
        lines.append(
            f"{i}. {m['market_name'][:45]}\n"
            f"   {m['price']:.1%}  {arrow} {abs(m['price_change']):.1%}  Vol: ${m['volume']:,.0f}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /market <search term>\nExample: /market election")
        return
    results = await search_market_snapshot(f"%{' '.join(context.args)}%")
    if not results:
        await update.message.reply_text("No markets found matching that term.")
        return
    lines = ["🔍 <b>Market Search</b>\n"]
    for r in results:
        slug = r.get("slug") or r["market_id"]
        lines.append(
            f"<b>{r['market_name'][:55]}</b>\n"
            f"Price: {r['price']:.1%}  Vol: ${r['volume']:,.0f}\n"
            f'<a href="https://polymarket.com/market/{slug}">View on Polymarket</a>\n'
        )
    await update.message.reply_text("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alerts = await get_recent_alerts(5)
    if not alerts:
        await update.message.reply_text("No alerts sent yet.")
        return
    EMOJI = {"price": "📈", "volume": "📊", "strong": "🚨"}
    lines = ["📋 <b>Recent Alerts</b>\n"]
    for a in alerts:
        lines.append(f"{EMOJI.get(a['signal_type'], '•')} {a['market_name'][:40]} — {_fmt_ts(a['sent_at'])}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_mystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    info = await get_subscriber_info(chat_id)
    if not info:
        await update.message.reply_text("You're not subscribed. Send /start to subscribe.")
        return
    prefs = await get_preferences(chat_id)
    qs, qe = prefs.get("quiet_start"), prefs.get("quiet_end")
    quiet_str = f"{qs:02d}:00–{qe:02d}:00 UTC" if qs is not None else "Off"
    mv = prefs.get("min_volume")
    pt = prefs.get("price_threshold")
    await update.message.reply_text(
        f"👤 <b>My Settings</b>\n\n"
        f"Subscribed  : {_fmt_ts(info['joined_at'])[:10]}\n"
        f"Filter      : {prefs.get('signal_filter', 'all')}\n"
        f"Quiet hours : {quiet_str}\n"
        f"Min volume  : {'$' + f'{mv:,.0f}' if mv else f'Global (${MIN_VOLUME:,})'}\n"
        f"Price move  : {f'{pt:.0%}' if pt else f'Global ({PRICE_CHANGE_THRESHOLD:.0%})'}\n\n"
        f"Change with /alerts /quiet /minvol /pricefilter",
        parse_mode="HTML",
    )
