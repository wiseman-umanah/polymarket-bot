from telegram import Update
from telegram.ext import ContextTypes
from bot.config import MIN_VOLUME, PRICE_CHANGE_THRESHOLD
from bot.db import get_preferences, upsert_preference


async def cmd_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        prefs = await get_preferences(chat_id)
        await update.message.reply_text(
            f"📡 <b>Alert Filter</b>\n\nCurrent: <b>{prefs.get('signal_filter', 'all')}</b>\n\n"
            "/alerts all    — all signals\n"
            "/alerts price  — price moves only\n"
            "/alerts volume — volume spikes only\n"
            "/alerts strong — combined signals only",
            parse_mode="HTML",
        )
        return
    choice = context.args[0].lower()
    if choice not in ("all", "price", "volume", "strong"):
        await update.message.reply_text("⚠️ Valid options: all, price, volume, strong")
        return
    await upsert_preference(chat_id, "signal_filter", choice)
    await update.message.reply_text(f"✅ Alert filter set to <b>{choice}</b>", parse_mode="HTML")


async def cmd_quiet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        prefs = await get_preferences(chat_id)
        qs, qe = prefs.get("quiet_start"), prefs.get("quiet_end")
        status = f"{qs:02d}:00–{qe:02d}:00 UTC" if qs is not None else "Off"
        await update.message.reply_text(
            f"🔕 <b>Quiet Hours</b>\n\nCurrent: {status}\n\n"
            "/quiet off       — disable\n"
            "/quiet 22 07     — silent 22:00–07:00 UTC",
            parse_mode="HTML",
        )
        return
    if context.args[0].lower() == "off":
        await upsert_preference(chat_id, "quiet_start", None)
        await upsert_preference(chat_id, "quiet_end", None)
        await update.message.reply_text("✅ Quiet hours disabled.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Usage: /quiet <start_hour> <end_hour>  (0–23 UTC)")
        return
    try:
        start, end = int(context.args[0]), int(context.args[1])
        if not (0 <= start <= 23 and 0 <= end <= 23):
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Hours must be integers 0–23.")
        return
    await upsert_preference(chat_id, "quiet_start", start)
    await upsert_preference(chat_id, "quiet_end", end)
    await update.message.reply_text(f"✅ Quiet hours: {start:02d}:00–{end:02d}:00 UTC")


async def cmd_minvol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        prefs = await get_preferences(chat_id)
        mv = prefs.get("min_volume")
        current = f"${mv:,.0f}" if mv else f"Global default (${MIN_VOLUME:,})"
        await update.message.reply_text(
            f"💰 <b>Minimum Volume</b>\n\nCurrent: {current}\n\n"
            "/minvol reset    — use global default\n"
            "/minvol 50000    — set to $50,000",
            parse_mode="HTML",
        )
        return
    if context.args[0].lower() == "reset":
        await upsert_preference(chat_id, "min_volume", None)
        await update.message.reply_text(f"✅ Reset to global default (${MIN_VOLUME:,})")
        return
    try:
        val = float(context.args[0].replace(",", ""))
        if val < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Enter a positive number, e.g. /minvol 50000")
        return
    await upsert_preference(chat_id, "min_volume", val)
    await update.message.reply_text(f"✅ Min volume set to ${val:,.0f}")


async def cmd_pricefilter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        prefs = await get_preferences(chat_id)
        pt = prefs.get("price_threshold")
        current = f"{pt:.0%}" if pt else f"Global default ({PRICE_CHANGE_THRESHOLD:.0%})"
        await update.message.reply_text(
            f"📏 <b>Price Move Filter</b>\n\nCurrent: {current}\n\n"
            "/pricefilter reset — use global default\n"
            "/pricefilter 0.08  — alert on 8%+ moves\n"
            "/pricefilter 8     — same, percentage form",
            parse_mode="HTML",
        )
        return
    if context.args[0].lower() == "reset":
        await upsert_preference(chat_id, "price_threshold", None)
        await update.message.reply_text(f"✅ Reset to global default ({PRICE_CHANGE_THRESHOLD:.0%})")
        return
    try:
        raw = float(context.args[0])
        val = raw / 100 if raw > 1 else raw
        if not (0 < val < 1):
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Enter a decimal (0.08) or percentage (8)")
        return
    await upsert_preference(chat_id, "price_threshold", val)
    await update.message.reply_text(f"✅ Price filter set to {val:.0%}")
