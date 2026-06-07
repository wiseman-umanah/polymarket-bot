import asyncio
import logging
import time
from bot.config import ADMIN_CHAT_ID

_THROTTLE_SECONDS = 600  # one notification per (logger, level) per 10 min — avoids flooding the admin


class TelegramAdminLogHandler(logging.Handler):
    """Forwards ERROR+ log records to the admin chat. Bind a bot + loop once the app starts."""

    def __init__(self, level=logging.ERROR):
        super().__init__(level=level)
        self._bot = None
        self._loop = None
        self._last_sent: dict[str, float] = {}

    def bind(self, bot, loop):
        self._bot = bot
        self._loop = loop

    def emit(self, record):
        if self._bot is None or not ADMIN_CHAT_ID:
            return

        key = f"{record.name}:{record.levelname}"
        now = time.monotonic()
        if now - self._last_sent.get(key, 0) < _THROTTLE_SECONDS:
            return
        self._last_sent[key] = now

        try:
            message = self.format(record)
        except Exception:
            return

        if len(message) > 3500:
            message = message[:3500] + "…"

        text = (
            f"🔴 {record.levelname} in {record.name}\n\n"
            f"{message}\n\n"
            f"(further {record.levelname} from this source muted for {_THROTTLE_SECONDS // 60} min)"
        )

        try:
            asyncio.run_coroutine_threadsafe(self._send(text), self._loop)
        except Exception:
            pass

    async def _send(self, text):
        try:
            await self._bot.send_message(chat_id=ADMIN_CHAT_ID, text=text)
        except Exception:
            pass


admin_log_handler = TelegramAdminLogHandler()
