"""Internal normalized representation of a Reddit post."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime

from app.reddit.htmlutil import strip_tags


@dataclass
class NormalizedPost:
    id: str
    subreddit: str
    title: str
    author: str
    original_url: str
    created_at: datetime
    selftext: str = ""
    selftext_html: str = ""
    external_url: str | None = None
    thumbnail_url: str | None = None
    categories: tuple[str, ...] = field(default_factory=tuple)
    fetched_at: datetime | None = None

    @property
    def guid(self) -> str:
        return f"reddit:{self.id}"

    @property
    def body_html(self) -> str:
        return self.selftext_html

    @property
    def body_text(self) -> str:
        if self.selftext:
            return self.selftext
        return strip_tags(self.selftext_html)

    def to_row(self) -> dict[str, object]:
        return {
            "id": self.id,
            "subreddit": self.subreddit,
            "title": self.title,
            "author": self.author,
            "original_url": self.original_url,
            "external_url": self.external_url,
            "thumbnail_url": self.thumbnail_url,
            "body_html": self.selftext_html,
            "body_text": self.body_text,
            "categories": json.dumps(list(self.categories)),
            "created_at": self.created_at.isoformat(),
            "fetched_at": (self.fetched_at or datetime.now(self.created_at.tzinfo)).isoformat(),
        }

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> NormalizedPost:
        categories = row["categories"] or "[]"
        try:
            parsed_categories = tuple(json.loads(categories))
        except (TypeError, ValueError):
            parsed_categories = ()
        return cls(
            id=row["id"],
            subreddit=row["subreddit"],
            title=row["title"],
            author=row["author"] or "",
            original_url=row["original_url"],
            external_url=row["external_url"],
            thumbnail_url=row["thumbnail_url"],
            selftext=row["body_text"] or "",
            selftext_html=row["body_html"] or "",
            categories=parsed_categories,
            created_at=datetime.fromisoformat(row["created_at"]),
            fetched_at=datetime.fromisoformat(row["fetched_at"]) if row["fetched_at"] else None,
        )
