from __future__ import annotations

import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Iterable

import feedparser
from apscheduler.schedulers.blocking import BlockingScheduler

from src.database import ArticleStore, SentArticle
from src.rss_crawler import Article, make_article_id
from src.telegram_bot import TelegramNews, TelegramNotifier
from src.translator import GeminiTranslator

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    text = _TAG_RE.sub("", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _parse_published(entry: dict):
    for key in ("published", "updated", "created"):
        val = entry.get(key)
        if val:
            try:
                return parsedate_to_datetime(val)
            except Exception:
                continue
    return None


def _fetch_one(url: str):
    return url, feedparser.parse(url)


def _articles_from_parsed(feed_url: str, parsed) -> list[Article]:
    feed_title = (getattr(parsed, "feed", {}) or {}).get("title")
    source = str(feed_title or feed_url)

    articles: list[Article] = []
    for entry in getattr(parsed, "entries", []) or []:
        url = entry.get("link") or entry.get("id")
        title = (entry.get("title") or "").strip()
        summary = entry.get("summary") or entry.get("description") or ""
        if not url or not title:
            continue

        articles.append(
            Article(
                article_id=make_article_id(url),
                url=url,
                title=_strip_html(title),
                summary=_strip_html(summary),
                source=source,
                published_at=_parse_published(entry),
            )
        )
    return articles


class NewsJob:
    def __init__(
        self,
        feed_urls: Iterable[str],
        store: ArticleStore,
        translator: GeminiTranslator,
        notifier: TelegramNotifier,
        enable_translation: bool = True,
    ) -> None:
        self._feed_urls = list(feed_urls)
        self._store = store
        self._translator = translator
        self._notifier = notifier
        self._enable_translation = enable_translation

    async def _process_article(self, art: Article) -> bool:
        if self._store.is_article_sent(art.article_id):
            return False

        if self._enable_translation:
            title_vi = self._translator.translate_to_vietnamese(art.title, context="football news title").text_vi
            summary_vi = self._translator.translate_to_vietnamese(art.summary, context="football news summary").text_vi
        else:
            title_vi = art.title
            summary_vi = art.summary

        await self._notifier.send_news_message(
            TelegramNews(
                source=art.source,
                title_vi=title_vi,
                summary_vi=summary_vi,
                url=art.url,
                title_en=art.title,
            )
        )

        self._store.mark_article_sent(
            SentArticle(article_id=art.article_id, url=art.url, title=art.title, source=art.source)
        )
        return True

    async def run_once(self) -> None:
        start = datetime.now()
        sent = 0
        errors = 0

        with ThreadPoolExecutor(max_workers=min(8, max(1, len(self._feed_urls)))) as ex:
            parsed_list = list(ex.map(_fetch_one, self._feed_urls))

        articles: list[Article] = []
        for feed_url, parsed in parsed_list:
            if getattr(parsed, "bozo", False):
                logger.warning("RSS bozo feed=%s error=%s", feed_url, getattr(parsed, "bozo_exception", None))
            articles.extend(_articles_from_parsed(feed_url, parsed))

        articles.sort(key=lambda a: a.published_at or datetime.min, reverse=True)
        for art in articles:
            try:
                did_send = await self._process_article(art)
                sent += 1 if did_send else 0
            except Exception:
                errors += 1
                logger.exception("Failed processing article url=%s", art.url)

        logger.info(
            "Job done feeds=%s articles=%s sent=%s errors=%s elapsed_s=%.2f",
            len(self._feed_urls),
            len(articles),
            sent,
            errors,
            (datetime.now() - start).total_seconds(),
        )


def start_scheduler(job: NewsJob, poll_interval_minutes: int) -> None:
    sched = BlockingScheduler()

    def _runner():
        asyncio.run(job.run_once())

    sched.add_job(_runner, "interval", minutes=poll_interval_minutes, max_instances=1, coalesce=True)
    sched.add_job(_runner, "date", run_date=datetime.now())
    logger.info("Scheduler started interval_minutes=%s", poll_interval_minutes)
    sched.start()
