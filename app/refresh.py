"""Scheduled Reddit refresh: the only component allowed to touch Reddit."""

from __future__ import annotations

import asyncio
import logging

from app.config import Settings
from app.db import Database
from app.reddit.source import RedditSource

logger = logging.getLogger(__name__)

STAGGER_SECONDS = 2.0


class Refresher:
    def __init__(self, settings: Settings, db: Database, source: RedditSource) -> None:
        self._settings = settings
        self._db = db
        self._source = source

    async def refresh_subreddit(self, subreddit: str) -> None:
        logger.info("source refresh start subreddit=%s", subreddit)
        try:
            posts = await self._source.list_posts(subreddit)
        except Exception as exc:  # noqa: BLE001 - keep serving stale cache
            logger.warning("source refresh failure subreddit=%s error=%s", subreddit, exc)
            return

        new_count = self._db.upsert_posts(posts)
        logger.info(
            "source refresh success subreddit=%s fetched=%d new=%d",
            subreddit,
            len(posts),
            new_count,
        )

    async def refresh_all(self) -> None:
        subreddits = self._settings.subreddits
        for index, subreddit in enumerate(subreddits):
            await self.refresh_subreddit(subreddit)
            if index < len(subreddits) - 1:
                await asyncio.sleep(STAGGER_SECONDS)

    async def run_forever(self) -> None:
        interval = self._settings.refresh_interval_minutes * 60
        while True:
            await self.refresh_all()
            logger.info("next source refresh in %d minutes", interval // 60)
            await asyncio.sleep(interval)
