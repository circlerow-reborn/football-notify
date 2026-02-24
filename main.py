from __future__ import annotations

import logging
import sys

from config.settings import Settings
from src.database import ArticleStore
from src.scheduler import NewsJob, start_scheduler
from src.telegram_bot import TelegramNotifier
from src.translator import GeminiTranslator


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def main() -> int:
    _configure_logging()
    logger = logging.getLogger("main")

    try:
        settings = Settings.load()
    except Exception as e:
        logger.error("Config error: %s", e)
        return 2

    store = ArticleStore(settings.mongodb_uri, settings.mongodb_db)
    translator = GeminiTranslator(api_key=settings.gemini_api_key, model_name=settings.gemini_model)
    notifier = TelegramNotifier(bot_token=settings.telegram_bot_token, chat_id=settings.telegram_chat_id)
    job = NewsJob(
        settings.rss_feeds,
        store=store,
        translator=translator,
        notifier=notifier,
        enable_translation=settings.enable_translation,
    )

    try:
        start_scheduler(job, poll_interval_minutes=settings.poll_interval_minutes)
        return 0
    except KeyboardInterrupt:
        logger.info("Shutting down (KeyboardInterrupt)")
        return 0
    except Exception:
        logger.exception("Fatal error")
        return 1
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
