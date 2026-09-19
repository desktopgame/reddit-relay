"""Reddit RSS based source (no authentication required)."""

from __future__ import annotations

import asyncio
import logging

import httpx

from app.config import Settings
from app.models.post import NormalizedPost
from app.reddit.atom import parse_atom_feed, parse_single_entry
from app.reddit.source import RedditSource

logger = logging.getLogger(__name__)

BASE = "https://www.reddit.com"

RETRYABLE_STATUS = {httpx.codes.TOO_MANY_REQUESTS, httpx.codes.SERVICE_UNAVAILABLE}


class RssRedditSource(RedditSource):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            headers={"User-Agent": settings.user_agent},
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
        )

    def _retry_delay(self, response: httpx.Response) -> float:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return max(1.0, float(retry_after))
            except ValueError:
                pass
        return self._settings.retry_delay_seconds

    async def _get_with_retry(self, url: str, label: str) -> httpx.Response:
        attempts = self._settings.max_retries + 1
        for attempt in range(1, attempts + 1):
            response = await self._client.get(url)
            logger.info(
                "reddit rss fetch %s status=%s attempt=%d/%d",
                label,
                response.status_code,
                attempt,
                attempts,
            )
            if response.status_code in RETRYABLE_STATUS and attempt < attempts:
                delay = self._retry_delay(response)
                logger.warning("reddit rate limited %s; retrying in %.0fs", label, delay)
                await asyncio.sleep(delay)
                continue
            response.raise_for_status()
            return response
        raise RuntimeError("unreachable")  # pragma: no cover

    async def list_posts(self, subreddit: str) -> list[NormalizedPost]:
        url = f"{BASE}/r/{subreddit}/.rss"
        response = await self._get_with_retry(url, label=f"subreddit={subreddit}")
        return parse_atom_feed(response.content, subreddit)

    async def get_post(self, post_id: str) -> NormalizedPost | None:
        short_id = post_id[3:] if post_id.startswith("t3_") else post_id
        url = f"{BASE}/comments/{short_id}/.rss"
        try:
            response = await self._get_with_retry(url, label=f"post_id={post_id}")
        except httpx.HTTPStatusError:
            return None
        return parse_single_entry(response.content, "")

    async def aclose(self) -> None:
        await self._client.aclose()
