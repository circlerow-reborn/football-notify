from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database as MongoDatabase
from pymongo.errors import DuplicateKeyError


@dataclass(frozen=True)
class SentArticle:
    article_id: str
    url: str
    title: str
    source: Optional[str] = None
    sent_at: Optional[datetime] = None


class ArticleStore:
    def __init__(self, mongodb_uri: str, db_name: str) -> None:
        self._client = MongoClient(mongodb_uri)
        self._db: MongoDatabase = self._client[db_name]
        self._sent: Collection = self._db["sent_articles"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._sent.create_index("article_id", unique=True, name="uniq_article_id")

    def is_article_sent(self, article_id: str) -> bool:
        return self._sent.find_one({"article_id": article_id}, {"_id": 1}) is not None

    def mark_article_sent(self, item: SentArticle) -> None:
        doc = {
            "article_id": item.article_id,
            "url": item.url,
            "title": item.title,
            "source": item.source,
            "sent_at": item.sent_at or datetime.now(UTC),
        }
        try:
            self._sent.insert_one(doc)
        except DuplicateKeyError:
            # Another worker/process inserted it first; treat as already-sent.
            return

    def close(self) -> None:
        self._client.close()
