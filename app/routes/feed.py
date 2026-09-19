"""Feed route: serves an RSS 2.0 feed from the cache only."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.datetimeutil import to_rfc822
from app.templating import templates
from app.validation import is_valid_subreddit

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/feed/{subreddit}")
def get_feed(subreddit: str, request: Request) -> Response:
    settings = request.app.state.settings
    canonical = settings.subreddit_map().get(subreddit.lower())
    if canonical is None or not is_valid_subreddit(subreddit):
        logger.info("feed request subreddit=%s result=unknown", subreddit)
        raise HTTPException(status_code=404, detail="Unknown subreddit")

    posts = request.app.state.db.list_posts(canonical, settings.max_posts_per_subreddit)
    logger.info("feed request subreddit=%s posts=%d", canonical, len(posts))

    return templates.TemplateResponse(
        request=request,
        name="feed.xml",
        context={
            "subreddit": canonical,
            "feed_url": settings.feed_url(canonical),
            "base_url": settings.base_url.rstrip("/"),
            "last_build": to_rfc822(datetime.now(UTC)),
            "posts": posts,
        },
        media_type="application/rss+xml; charset=utf-8",
    )
