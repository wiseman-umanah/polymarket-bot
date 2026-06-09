from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from bot.config import (
    MIN_VOLUME, PRICE_CHANGE_THRESHOLD, ALERT_COOLDOWN_MINUTES,
    LOOKBACK_MINUTES, VOLUME_SPIKE_MULTIPLIER, ADMIN_CHAT_ID,
)
from bot.state import state
from bot.keyboards import main_menu_keyboard, unsubscribe_feedback_keyboard, settings_menu_keyboard
from bot.db import (
    add_subscriber, remove_subscriber, count_subscribers,
    count_alerts_today, get_subscriber_info, get_preferences,
    get_top_movers, search_market_snapshot, get_recent_alerts,
)

X_LINK = "https://x.com/0xwisemanumanah"


def _fmt_ts(ts) -> str:
    if hasattr(ts, "strftime"):
        return ts.strftime("%m-%d %H:%M UTC")
    return str(ts)[:16]


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await add_subscriber(chat_id, update.effective_user.username)
    await update.message.reply_text(
        "👋 <b>Welcome to PolyShock!</b>\n\n"
        "You're subscribed to real-time Polymarket alerts.\n\n"
        "Alerts fire when:\n"
        "📈 Price moves ≥4% within ~5 minutes\n"
        "📊 Volume spikes ≥2× the recent average\n"
        "🚨 Both happen together (strong signal)\n\n"
        "Use the menu below to explore — top movers, market search, "
        "your stats and settings. Send /help anytime for commands that take input.\n\n"
        "/stop — unsubscribe",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard,
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
        "📖 <b>PolyShock Help</b>\n\n"
        "Use the menu below to browse top movers, search markets, view alert "
        "history, and check or change your settings.\n\n"
        "<b>Commands that take input:</b>\n"
        "<code>/market &lt;term&gt;</code> — search markets by name\n"
        "<code>/alerts all|price|volume|strong</code> — filter signal types\n"
        "<code>/quiet HH HH|off</code> — set quiet hours in UTC\n"
        "<code>/minvol &lt;amount&gt;|reset</code> — your minimum market volume\n"
        "<code>/pricefilter &lt;value&gt;|reset</code> — your price move threshold\n\n"
        "<code>/thresholds</code> — view global signal settings\n"
        "<code>/stop</code> — unsubscribe anytime"
    )

    if is_admin:
        text += (
            "\n\n<b>Admin only</b>\n"
            "/admin         — pause/resume all alerts (inline button)\n"
            "/adminstats    — subscriber count, stats, mode\n"
            "/broadcast &lt;text&gt; — push a message to all subscribers\n"
        )

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard)


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await remove_subscriber(update.effective_chat.id)
    await update.message.reply_text(
        "👋 Unsubscribed. Send /start anytime to resubscribe.\n\n"
        "Mind telling us why you left? It really helps us improve. (totally optional)",
        reply_markup=unsubscribe_feedback_keyboard(),
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id == ADMIN_CHAT_ID:
        uptime = datetime.now() - state.start_time
        h, rem = divmod(int(uptime.total_seconds()), 3600)
        m = rem // 60
        await update.message.reply_text(
            f"📊 <b>Bot Status</b> (admin view)\n\n"
            f"Uptime      : {h}h {m}m\n"
            f"Markets     : {state.last_market_count} monitored\n"
            f"Subscribers : {await count_subscribers()}\n"
            f"Alerts today: {await count_alerts_today()}\n"
            f"State       : {'⏸ Paused' if state.paused else '✅ Running'}",
            parse_mode="HTML",
        )
        return

    await update.message.reply_text(
        "✅ <b>PolyShock is active.</b>\n\n"
        "Built by Wiseman\n"
        f'<a href="{X_LINK}">Follow on X</a>',
        parse_mode="HTML",
        disable_web_page_preview=True,
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
        f"Price move  : {f'{pt:.0%}' if pt else f'Global ({PRICE_CHANGE_THRESHOLD:.0%})'}",
        parse_mode="HTML",
        reply_markup=settings_menu_keyboard(),
    )
