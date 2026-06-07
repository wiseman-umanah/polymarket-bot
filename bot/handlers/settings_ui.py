from telegram import Update
from telegram.ext import ContextTypes
from bot.config import MIN_VOLUME, PRICE_CHANGE_THRESHOLD
from bot.db import upsert_preference
from bot.keyboards import numpad_keyboard
from bot.handlers.preferences import parse_price_filter, parse_min_volume, parse_quiet_hour

_PROMPTS = {
    "pricefilter": "📐 Enter your price move threshold — e.g. <code>8</code> for 8%, or <code>0.08</code>:",
    "minvol": "💰 Enter your minimum market volume in USD — e.g. <code>50000</code>:",
    "quiet_start": "🌙 Enter the START hour for quiet hours (UTC, 0–23):",
    "quiet_end": "🌙 Enter the END hour for quiet hours (UTC, 0–23):",
}

_DECIMAL_SETTINGS = {"pricefilter", "minvol"}


def _numpad_text(setting: str, buffer: str) -> str:
    return f"{_PROMPTS[setting]}\n\n<code>{buffer or '_'}</code>"


async def _show_numpad(query, setting: str, buffer: str = ""):
    await query.edit_message_text(
        _numpad_text(setting, buffer),
        parse_mode="HTML",
        reply_markup=numpad_keyboard(buffer, allow_decimal=setting in _DECIMAL_SETTINGS),
    )


async def settings_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'set a custom value' vs 'reset/turn off' choice for numeric settings."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    _, setting, action = query.data.split("_", 2)

    if action == "custom":
        entry_setting = "quiet_start" if setting == "quiet" else setting
        context.user_data["numpad"] = {"setting": entry_setting, "buffer": ""}
        await _show_numpad(query, entry_setting)
        return

    context.user_data.pop("numpad", None)
    if setting == "pricefilter":
        await upsert_preference(chat_id, "price_threshold", None)
        await query.edit_message_text(f"✅ Reset to global default ({PRICE_CHANGE_THRESHOLD:.0%})")
    elif setting == "minvol":
        await upsert_preference(chat_id, "min_volume", None)
        await query.edit_message_text(f"✅ Reset to global default (${MIN_VOLUME:,})")
    elif setting == "quiet":
        await upsert_preference(chat_id, "quiet_start", None)
        await upsert_preference(chat_id, "quiet_end", None)
        await query.edit_message_text("✅ Quiet hours turned off.")


async def reset_all_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    context.user_data.pop("numpad", None)

    if query.data == "resetall_cancel":
        await query.edit_message_text("No changes made.")
        return

    await upsert_preference(chat_id, "signal_filter", "all")
    await upsert_preference(chat_id, "quiet_start", None)
    await upsert_preference(chat_id, "quiet_end", None)
    await upsert_preference(chat_id, "min_volume", None)
    await upsert_preference(chat_id, "price_threshold", None)
    await query.edit_message_text("✅ All your settings have been reset to the global defaults.")


async def alert_filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    choice = query.data.removeprefix("setaf_")
    await upsert_preference(chat_id, "signal_filter", choice)
    await query.edit_message_text(f"✅ Alert filter set to <b>{choice}</b>", parse_mode="HTML")


async def numpad_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    np_state = context.user_data.get("numpad")
    if not np_state:
        await query.answer("This menu has expired — open Settings again.", show_alert=True)
        return

    data = query.data
    setting = np_state["setting"]
    buffer = np_state["buffer"]

    if data == "np_noop":
        await query.answer()
        return
    if data == "np_cancel":
        context.user_data.pop("numpad", None)
        await query.answer("Cancelled")
        await query.edit_message_text("No changes made.")
        return
    if data == "np_back":
        np_state["buffer"] = buffer[:-1]
        await query.answer()
        await _show_numpad(query, setting, np_state["buffer"])
        return
    if data == "np_dot":
        if setting in _DECIMAL_SETTINGS and "." not in buffer:
            np_state["buffer"] = (buffer or "0") + "."
        await query.answer()
        await _show_numpad(query, setting, np_state["buffer"])
        return
    if data.startswith("npd_"):
        if len(buffer) < 12:
            np_state["buffer"] = buffer + data.removeprefix("npd_")
        await query.answer()
        await _show_numpad(query, setting, np_state["buffer"])
        return
    if data == "np_confirm":
        await _confirm_numpad(query, context, np_state)
        return


async def _confirm_numpad(query, context, np_state):
    setting = np_state["setting"]
    buffer = np_state["buffer"]
    chat_id = query.message.chat.id

    if setting == "pricefilter":
        val = parse_price_filter(buffer) if buffer else None
        if val is None:
            await query.answer("Enter a value between 0 and 100", show_alert=True)
            return
        await upsert_preference(chat_id, "price_threshold", val)
        context.user_data.pop("numpad", None)
        await query.edit_message_text(f"✅ Price filter set to {val:.0%}")

    elif setting == "minvol":
        val = parse_min_volume(buffer) if buffer else None
        if val is None:
            await query.answer("Enter a positive number", show_alert=True)
            return
        await upsert_preference(chat_id, "min_volume", val)
        context.user_data.pop("numpad", None)
        await query.edit_message_text(f"✅ Min volume set to ${val:,.0f}")

    elif setting == "quiet_start":
        hour = parse_quiet_hour(buffer) if buffer else None
        if hour is None:
            await query.answer("Enter an hour 0–23", show_alert=True)
            return
        np_state["setting"] = "quiet_end"
        np_state["start_hour"] = hour
        np_state["buffer"] = ""
        await query.answer()
        await _show_numpad(query, "quiet_end")

    elif setting == "quiet_end":
        end_hour = parse_quiet_hour(buffer) if buffer else None
        if end_hour is None:
            await query.answer("Enter an hour 0–23", show_alert=True)
            return
        start_hour = np_state["start_hour"]
        await upsert_preference(chat_id, "quiet_start", start_hour)
        await upsert_preference(chat_id, "quiet_end", end_hour)
        context.user_data.pop("numpad", None)
        await query.edit_message_text(f"✅ Quiet hours set: {start_hour:02d}:00–{end_hour:02d}:00 UTC")
