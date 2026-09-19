"""Reddit RSS based source (no authentication required)."""

from __future__ import annotations

import logging

import httpx

from app.config import Settings
from app.models.post import NormalizedPost
from app.reddit.atom import parse_atom_feed, parse_single_entry
from app.reddit.source import RedditSource

logger = logging.getLogger(__name__)

BASE = "https://www.reddit.com"


class RssRedditSource(RedditSource):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            headers={"User-Agent": settings.user_agent},
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
        )

    async def list_posts(self, subreddit: str) -> list[NormalizedPost]:
        url = f"{BASE}/r/{subreddit}/.rss"
        response = await self._client.get(url)
        logger.info("reddit rss fetch subreddit=%s status=%s", subreddit, response.status_code)
        response.raise_for_status()
        return parse_atom_feed(response.content, subreddit)

    async def get_post(self, post_id: str) -> NormalizedPost | None:
        short_id = post_id[3:] if post_id.startswith("t3_") else post_id
        url = f"{BASE}/comments/{short_id}/.rss"
        response = await self._client.get(url)
        logger.info("reddit rss fetch post_id=%s status=%s", post_id, response.status_code)
        if response.status_code != httpx.codes.OK:
            return None
        return parse_single_entry(response.content, "")

    async def aclose(self) -> None:
        await self._client.aclose()
