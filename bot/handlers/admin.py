from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.config import ADMIN_CHAT_ID, WEBHOOK_URL
from bot.state import state
from bot.notifier import broadcast_message
from bot.db import count_subscribers, count_alerts_today
import logging

logger = logging.getLogger(__name__)


def _is_admin(chat_id: int) -> bool:
    return chat_id == ADMIN_CHAT_ID


def _admin_keyboard() -> InlineKeyboardMarkup:
    label = "▶️ Resume All" if state.paused else "⏸ Pause All"
    data = "admin_resume" if state.paused else "admin_pause"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=data)]])


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_chat.id):
        await update.message.reply_text("⛔ Not authorized.")
        return
    await update.message.reply_text(
        f"🔧 <b>Admin Panel</b>\n\nState: {'⏸ Paused' if state.paused else '✅ Running'}",
        reply_markup=_admin_keyboard(),
        parse_mode="HTML",
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not _is_admin(query.from_user.id):
        await query.answer("⛔ Not authorized.", show_alert=True)
        return
    await query.answer()

    if query.data == "admin_pause":
        state.paused = True
        await broadcast_message(context.bot, "⏸ Bot paused for maintenance. Alerts will resume shortly.")
        logger.info("Bot paused by admin")
    elif query.data == "admin_resume":
        state.paused = False
        await broadcast_message(context.bot, "▶️ Bot resumed. Monitoring markets.")
        logger.info("Bot resumed by admin")

    await query.edit_message_text(
        f"🔧 <b>Admin Panel</b>\n\nState: {'⏸ Paused' if state.paused else '✅ Running'}",
        reply_markup=_admin_keyboard(),
        parse_mode="HTML",
    )


async def cmd_adminstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_chat.id):
        await update.message.reply_text("⛔ Not authorized.")
        return
    uptime = datetime.now() - state.start_time
    h, rem = divmod(int(uptime.total_seconds()), 3600)
    m = rem // 60
    await update.message.reply_text(
        f"🔧 <b>Admin Stats</b>\n\n"
        f"Subscribers   : {await count_subscribers()}\n"
        f"Alerts today  : {await count_alerts_today()}\n"
        f"Markets       : {state.last_market_count}\n"
        f"Uptime        : {h}h {m}m\n"
        f"State         : {'⏸ Paused' if state.paused else '✅ Running'}\n"
        f"Mode          : {'Webhook' if WEBHOOK_URL else 'Polling'}\n"
        f"Poll failures : {state.consecutive_failures}",
        parse_mode="HTML",
    )


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_chat.id):
        await update.message.reply_text("⛔ Not authorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message text>")
        return
    text = " ".join(context.args)
    await broadcast_message(context.bot, f"📢 {text}")
    subs = await count_subscribers()
    await update.message.reply_text(f"✅ Broadcast sent to {subs} subscriber(s).")
    logger.info(f"Admin broadcast: {text[:80]}")
