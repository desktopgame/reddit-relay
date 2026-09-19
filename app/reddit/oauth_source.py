"""Placeholder for the future Reddit OAuth API source.

Kept as an explicit stub so the source interface stays swappable.  Credentials
must never leak into the rendering/caching layers; this module is the only
place they would live.
"""

from __future__ import annotations

from app.config import Settings
from app.models.post import NormalizedPost
from app.reddit.source import RedditSource


class OAuthRedditSource(RedditSource):
    def __init__(self, settings: Settings) -> None:  # pragma: no cover - future work
        self._settings = settings
        raise NotImplementedError(
            "Reddit OAuth source is not implemented yet; use RssRedditSource."
        )

    async def list_posts(self, subreddit: str) -> list[NormalizedPost]:  # pragma: no cover
        raise NotImplementedError

    async def get_post(self, post_id: str) -> NormalizedPost | None:  # pragma: no cover
        raise NotImplementedError

    async def aclose(self) -> None:  # pragma: no cover - future work
        return None
