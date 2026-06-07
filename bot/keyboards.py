from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

BTN_TOP = "📈 Top Movers"
BTN_SEARCH = "🔍 Search Market"
BTN_HISTORY = "📋 History"
BTN_SETTINGS = "⚙️ Settings"
BTN_MYSTATS = "👤 My Stats"
BTN_HELP = "❓ Help"

main_menu_keyboard = ReplyKeyboardMarkup(
    [
        [BTN_TOP, BTN_SEARCH],
        [BTN_HISTORY, BTN_SETTINGS],
        [BTN_MYSTATS, BTN_HELP],
    ],
    resize_keyboard=True,
)


def settings_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎯 Alert Filter", callback_data="menu_alerts"),
            InlineKeyboardButton("🌙 Quiet Hours", callback_data="menu_quiet"),
        ],
        [
            InlineKeyboardButton("💰 Min Volume", callback_data="menu_minvol"),
            InlineKeyboardButton("📐 Price Filter", callback_data="menu_pricefilter"),
        ],
        [InlineKeyboardButton("🔄 Reset all to defaults", callback_data="menu_resetall")],
    ])


def reset_all_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, reset everything", callback_data="resetall_confirm")],
        [InlineKeyboardButton("✖ Cancel", callback_data="resetall_cancel")],
    ])


def numeric_setting_choice_keyboard(setting: str, reset_label: str) -> InlineKeyboardMarkup:
    """'Set a custom value' vs 'reset/turn off' — entry point for the numpad flow."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Set a custom value", callback_data=f"numset_{setting}_custom")],
        [InlineKeyboardButton(reset_label, callback_data=f"numset_{setting}_reset")],
    ])


def numpad_keyboard(buffer: str, allow_decimal: bool = True) -> InlineKeyboardMarkup:
    dot = (
        InlineKeyboardButton(".", callback_data="np_dot")
        if allow_decimal
        else InlineKeyboardButton(" ", callback_data="np_noop")
    )
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(str(d), callback_data=f"npd_{d}") for d in range(1, 4)],
        [InlineKeyboardButton(str(d), callback_data=f"npd_{d}") for d in range(4, 7)],
        [InlineKeyboardButton(str(d), callback_data=f"npd_{d}") for d in range(7, 10)],
        [dot, InlineKeyboardButton("0", callback_data="npd_0"), InlineKeyboardButton("⌫", callback_data="np_back")],
        [InlineKeyboardButton("✖ Cancel", callback_data="np_cancel"), InlineKeyboardButton("✓ Confirm", callback_data="np_confirm")],
    ])


def alert_filter_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌐 All", callback_data="setaf_all"),
            InlineKeyboardButton("📈 Price", callback_data="setaf_price"),
        ],
        [
            InlineKeyboardButton("📊 Volume", callback_data="setaf_volume"),
            InlineKeyboardButton("🚨 Strong", callback_data="setaf_strong"),
        ],
    ])


def unsubscribe_feedback_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("😴 Too many alerts", callback_data="unsub_too_many")],
        [InlineKeyboardButton("🤷 Not relevant to me", callback_data="unsub_not_relevant")],
        [InlineKeyboardButton("🔍 Found something better", callback_data="unsub_better")],
        [InlineKeyboardButton("💬 Other reason", callback_data="unsub_other")],
        [InlineKeyboardButton("⏭ Skip", callback_data="unsub_skip")],
    ])
