import html
from telegram import Update
from telegram.ext import ContextTypes
from bot.config import ADMIN_CHAT_ID

_REASON_LABELS = {
    "unsub_too_many": "😴 Too many alerts",
    "unsub_not_relevant": "🤷 Not relevant to them",
    "unsub_better": "🔍 Found something better",
}


async def notify_admin_unsub_feedback(bot, update: Update, reason: str):
    if not ADMIN_CHAT_ID:
        return
    user = update.effective_user
    handle = f"@{user.username}" if user.username else f"id {user.id}"
    try:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=(
                f"📤 <b>Unsubscribe feedback</b>\n\n"
                f"{html.escape(handle)} (chat {update.effective_chat.id}):\n"
                f"{html.escape(reason)}"
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass


async def unsubscribe_feedback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "unsub_other":
        context.user_data["awaiting_unsub_feedback"] = True
        await query.edit_message_text("Type your reason below 👇")
        return

    if data == "unsub_skip":
        await query.edit_message_text("No problem — thanks anyway! 🙏")
        return

    reason = _REASON_LABELS.get(data)
    if reason:
        await notify_admin_unsub_feedback(context.bot, update, reason)
    await query.edit_message_text("Thanks for letting us know — we'll work on it. 🙏")
