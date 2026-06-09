from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from bot.config import ADMIN_CHAT_ID, WEBHOOK_URL
from bot.state import state
from bot.notifier import broadcast_message
from bot.db import count_subscribers, count_alerts_today, get_all_subscribers
import logging

logger = logging.getLogger(__name__)

# Active polls: {poll_id: {"question": str, "options": list[str], "voters": dict[user_id, option_text]}}
# Populated when a poll is broadcast; entries persist until bot restart.
_active_polls: dict[str, dict] = {}


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


async def cmd_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_chat.id):
        await update.message.reply_text("⛔ Not authorized.")
        return

    raw = " ".join(context.args)
    parts = [p.strip() for p in raw.split("|") if p.strip()]

    if len(parts) < 3:
        await update.message.reply_text(
            "Usage: /poll Question | Option A | Option B | Option C\n"
            "At least 2 options required, max 10."
        )
        return

    question = f"{parts[0]}\n\n⚠️ Your first selection is final — votes cannot be changed."
    options = parts[1:]

    if len(options) > 10:
        await update.message.reply_text("⚠️ Telegram polls support max 10 options.")
        return

    subscribers = await get_all_subscribers()
    sent = 0
    for chat_id in subscribers:
        try:
            msg = await context.bot.send_poll(
                chat_id=chat_id,
                question=question,
                options=options,
                is_anonymous=False,
                allows_multiple_answers=False,
            )
            # Each send_poll creates a unique poll_id — register all of them
            _active_polls[msg.poll.id] = {
                "question": question,
                "options": options,
                "voters": {},
            }
            sent += 1
        except TelegramError as e:
            logger.warning(f"cmd_poll → {chat_id}: {e}")

    await update.message.reply_text(
        f"✅ Poll sent to {sent} subscriber(s).\n"
        f"Votes will be forwarded here as they come in.\n\n"
        f"<b>Q:</b> {question}\n" +
        "\n".join(f"  • {o}" for o in options),
        parse_mode="HTML",
    )
    logger.info(f"Poll broadcast to {sent} subscribers: {question[:60]}")


async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    poll_id = answer.poll_id
    user = answer.user
    option_ids = answer.option_ids

    poll = _active_polls.get(poll_id)
    if not poll:
        return  # not one of our tracked polls

    if user.id in poll["voters"]:
        return  # ignore vote changes — first vote is final

    if not option_ids:
        return  # vote retracted before committing

    chosen = poll["options"][option_ids[0]]
    poll["voters"][user.id] = chosen

    handle = f"@{user.username}" if user.username else user.first_name
    total = len(poll["voters"])

    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=(
                f"📊 <b>Poll vote #{total}</b>\n"
                f"{handle} → <b>{chosen}</b>\n"
                f"<i>{poll['question']}</i>"
            ),
            parse_mode="HTML",
        )
    except TelegramError as e:
        logger.warning(f"handle_poll_answer → admin report failed: {e}")
