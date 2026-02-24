from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _split_csv(val: str) -> list[str]:
    parts = [p.strip() for p in (val or "").split(",")]
    return [p for p in parts if p]


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_chat_id: str
    gemini_api_key: str
    gemini_model: str
    enable_translation: bool
    mongodb_uri: str
    mongodb_db: str
    rss_feeds: list[str]
    poll_interval_minutes: int

    @staticmethod
    def load() -> "Settings":
        load_dotenv()

        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip() or "gemini-1.5-flash"
        mongodb_uri = os.getenv("MONGODB_URI", "").strip()
        mongodb_db = os.getenv("MONGODB_DB", "football_news").strip() or "football_news"
        rss_feeds = _split_csv(os.getenv("RSS_FEEDS", ""))

        enable_translation_raw = os.getenv("ENABLE_TRANSLATION", "false").strip().lower()
        enable_translation = enable_translation_raw in {"1", "true", "yes", "y", "on"}

        poll_interval_raw = os.getenv("POLL_INTERVAL_MINUTES", "5").strip() or "5"
        poll_interval_minutes = int(poll_interval_raw)

        missing: list[str] = []
        if not telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not telegram_chat_id:
            missing.append("TELEGRAM_CHAT_ID")
        if not gemini_api_key:
            missing.append("GEMINI_API_KEY")
        if not mongodb_uri:
            missing.append("MONGODB_URI")
        if not rss_feeds:
            missing.append("RSS_FEEDS")

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        if poll_interval_minutes <= 0:
            raise ValueError("POLL_INTERVAL_MINUTES must be > 0")

        return Settings(
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
            enable_translation=enable_translation,
            mongodb_uri=mongodb_uri,
            mongodb_db=mongodb_db,
            rss_feeds=rss_feeds,
            poll_interval_minutes=poll_interval_minutes,
        )
