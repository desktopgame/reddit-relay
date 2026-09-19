"""reddit-relay: local read-only Reddit -> Karakeep relay."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request

from app.config import get_settings
from app.db import Database
from app.reddit.rss_source import RssRedditSource
from app.refresh import Refresher
from app.routes import feed, post

logger = logging.getLogger(__name__)

settings = get_settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = Database(settings.db_path)
    db.init()
    source = RssRedditSource(settings)
    refresher = Refresher(settings, db, source)

    app.state.settings = settings
    app.state.db = db
    app.state.source = source
    app.state.refresher = refresher

    task = asyncio.create_task(refresher.run_forever())
    logger.info(
        "reddit-relay started subreddits=%s db=%s",
        ",".join(settings.subreddits),
        settings.db_path,
    )
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        await source.aclose()
        logger.info("reddit-relay stopped")


app = FastAPI(title="reddit-relay", lifespan=lifespan)
app.include_router(feed.router)
app.include_router(post.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    logger.info("%s %s -> %s", request.method, request.url.path, response.status_code)
    return response


@app.get("/health")
def health(request: Request) -> dict[str, object]:
    db = request.app.state.db
    return {
        "status": "ok",
        "last_refresh": db.get_meta("last_refresh"),
        "cached_posts": db.count_posts(),
    }
