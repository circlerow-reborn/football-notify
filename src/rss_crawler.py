from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Iterable, Optional
from urllib.parse import urlparse

import feedparser

logger = logging.getLogger(__name__)


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    text = _TAG_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def _get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc or "unknown"
    except Exception:
        return "unknown"


def make_article_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _parse_published(entry: dict) -> Optional[datetime]:
    for key in ("published", "updated", "created"):
        val = entry.get(key)
        if val:
            try:
                return parsedate_to_datetime(val)
            except Exception:
                continue
    return None


@dataclass(frozen=True)
class Article:
    article_id: str
    url: str
    title: str
    summary: str
    source: str
    published_at: Optional[datetime] = None


def fetch_articles(feed_urls: Iterable[str]) -> list[Article]:
    articles: list[Article] = []

    for feed_url in feed_urls:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception:
            logger.exception("Failed to parse RSS feed: %s", feed_url)
            continue

        if getattr(parsed, "bozo", False):
            logger.warning("RSS bozo feed=%s error=%s", feed_url, getattr(parsed, "bozo_exception", None))

        feed_title = (getattr(parsed, "feed", {}) or {}).get("title")
        source = feed_title or _get_domain(feed_url)

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
                    source=str(source),
                    published_at=_parse_published(entry),
                )
            )

    articles.sort(key=lambda a: a.published_at or datetime.min, reverse=True)
    return articles
