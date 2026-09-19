"""Reddit source interface.

Different acquisition strategies (RSS today, OAuth API later) implement this
interface so the rendering/caching layers never depend on a concrete source.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.post import NormalizedPost


class RedditSource(ABC):
    @abstractmethod
    async def list_posts(self, subreddit: str) -> list[NormalizedPost]:
        """Return the current listing for ``subreddit``."""

    @abstractmethod
    async def get_post(self, post_id: str) -> NormalizedPost | None:
        """Return a single post, or ``None`` when it cannot be fetched."""

    @abstractmethod
    async def aclose(self) -> None:
        """Release any underlying network resources."""
