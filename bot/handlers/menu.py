from telegram import Update
from telegram.ext import ContextTypes
from bot.config import MIN_VOLUME, PRICE_CHANGE_THRESHOLD
from bot.db import get_preferences
from bot.keyboards import (
    BTN_TOP, BTN_SEARCH, BTN_HISTORY, BTN_SETTINGS, BTN_MYSTATS, BTN_HELP,
    settings_menu_keyboard, alert_filter_keyboard, numeric_setting_choice_keyboard,
    reset_all_confirm_keyboard,
)
from bot.handlers.user import cmd_top, cmd_history, cmd_mystats, cmd_help
from bot.handlers.unsubscribe import notify_admin_unsub_feedback


async def handle_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.pop("awaiting_unsub_feedback", False):
        await notify_admin_unsub_feedback(context.bot, update, update.message.text)
        await update.message.reply_text("Thanks for letting us know — we'll work on it. 🙏")
        return

    text = update.message.text

    if text == BTN_TOP:
        await cmd_top(update, context)
    elif text == BTN_SEARCH:
        await update.message.reply_text(
            "🔍 Send <code>/market &lt;term&gt;</code> to search — e.g. <code>/market election</code>",
            parse_mode="HTML",
        )
    elif text == BTN_HISTORY:
        await cmd_history(update, context)
    elif text == BTN_SETTINGS:
        await update.message.reply_text(
            "⚙️ <b>Settings</b>\n\n"
            "🎯 <b>Alert Filter</b> — which signal types you receive\n"
            "🌙 <b>Quiet Hours</b> — mute alerts during certain hours\n"
            "💰 <b>Min Volume</b> — minimum market volume to alert on\n"
            "📐 <b>Price Filter</b> — minimum price move % to alert on\n\n"
            "Tap one below to view and change it.",
            parse_mode="HTML",
            reply_markup=settings_menu_keyboard(),
        )
    elif text == BTN_MYSTATS:
        await cmd_mystats(update, context)
    elif text == BTN_HELP:
        await cmd_help(update, context)
    else:
        await update.message.reply_text("I didn't quite catch that — try a button below or send /help.")


async def settings_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    prefs = await get_preferences(chat_id)
    data = query.data

    if data == "menu_alerts":
        current = prefs.get("signal_filter") or "all"
        await query.edit_message_text(
            "🎯 <b>Alert Filter</b>\n"
            "Choose which signal types trigger your alerts — price moves, "
            "volume spikes, both together (strong), or all of them.\n\n"
            f"Current: <code>{current}</code>\n\nTap one to switch:",
            parse_mode="HTML",
            reply_markup=alert_filter_keyboard(),
        )
    elif data == "menu_quiet":
        qs, qe = prefs.get("quiet_start"), prefs.get("quiet_end")
        current = f"{qs:02d}:00–{qe:02d}:00 UTC" if qs is not None else "Off"
        await query.edit_message_text(
            "🌙 <b>Quiet Hours</b>\n"
            "Mute alerts during a daily window — handy while you're asleep "
            "or busy. Times are in UTC.\n\n"
            f"Current: <code>{current}</code>",
            parse_mode="HTML",
            reply_markup=numeric_setting_choice_keyboard("quiet", "🔕 Turn off"),
        )
    elif data == "menu_minvol":
        mv = prefs.get("min_volume")
        current = f"${mv:,.0f}" if mv else f"Global default (${MIN_VOLUME:,})"
        await query.edit_message_text(
            "💰 <b>Min Volume</b>\n"
            "Only get alerts for markets with at least this much total "
            "trading volume — filters out thin, low-interest markets.\n\n"
            f"Current: <code>{current}</code>",
            parse_mode="HTML",
            reply_markup=numeric_setting_choice_keyboard("minvol", f"↩️ Use global default (${MIN_VOLUME:,})"),
        )
    elif data == "menu_pricefilter":
        pt = prefs.get("price_threshold")
        current = f"{pt:.0%}" if pt else f"Global default ({PRICE_CHANGE_THRESHOLD:.0%})"
        await query.edit_message_text(
            "📐 <b>Price Filter</b>\n"
            "Only get alerts when a market's price moves by at least this "
            "percentage within the lookback window.\n\n"
            f"Current: <code>{current}</code>",
            parse_mode="HTML",
            reply_markup=numeric_setting_choice_keyboard("pricefilter", f"↩️ Use global default ({PRICE_CHANGE_THRESHOLD:.0%})"),
        )
    elif data == "menu_resetall":
        await query.edit_message_text(
            "⚠️ This will reset <b>all</b> of your settings — alert filter, "
            "quiet hours, min volume, and price filter — back to the global "
            "defaults.\n\nContinue?",
            parse_mode="HTML",
            reply_markup=reset_all_confirm_keyboard(),
        )
