from __future__ import annotations

import html
import logging
import time
from dataclasses import dataclass
from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

TELEGRAM_MAX_MESSAGE_LEN = 4096


@dataclass(frozen=True)
class TelegramNews:
    source: str
    title_vi: str
    summary_vi: str
    url: str
    title_en: Optional[str] = None


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    if max_len <= 1:
        return text[:max_len]
    return text[: max_len - 1].rstrip() + "…"


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._bot = Bot(token=bot_token)
        self._chat_id = chat_id

    async def send_news_message(self, news: TelegramNews) -> None:
        header = f"⚽ <b>{html.escape(news.source)}</b>\n\n"
        title = f"<b>{html.escape(news.title_vi)}</b>\n\n"
        summary = html.escape(news.summary_vi or "").strip()
        link = f"\n\n🔗 Read more: {html.escape(news.url)}"

        max_summary_len = TELEGRAM_MAX_MESSAGE_LEN - (len(header) + len(title) + len(link))
        max_summary_len = max(0, max_summary_len)
        body = _truncate(summary, max_summary_len)
        text = header + title + body + link

        last_err: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                await self._bot.send_message(
                    chat_id=self._chat_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=False,
                )
                return
            except Exception as e:
                last_err = e
                logger.warning("Telegram send failed attempt=%s err=%s", attempt, e)
                time.sleep(min(2**attempt, 8))

        raise RuntimeError(f"Failed to send Telegram message: {last_err}")
