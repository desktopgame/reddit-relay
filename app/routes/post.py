"""Post route: serves cached post HTML to the Karakeep crawler."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.templating import templates
from app.validation import is_valid_post_id

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/post/{post_id}")
def get_post(post_id: str, request: Request) -> Response:
    if not is_valid_post_id(post_id):
        raise HTTPException(status_code=404, detail="Post not found")

    post = request.app.state.db.get_post(post_id)
    if post is None:
        logger.info("post request id=%s result=cache_miss", post_id)
        raise HTTPException(status_code=404, detail="Post not cached")

    logger.info("post request id=%s result=cache_hit", post_id)
    return templates.TemplateResponse(
        request=request,
        name="post.html",
        context={
            "post": post,
            "relay_url": request.app.state.settings.post_url(post_id),
        },
    )
