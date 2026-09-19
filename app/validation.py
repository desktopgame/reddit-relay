"""Input validation shared by the public routes."""

from __future__ import annotations

import re

SUBREDDIT_RE = re.compile(r"^[A-Za-z0-9_]{2,21}$")
POST_ID_RE = re.compile(r"^t3_[a-z0-9]+$")


def is_valid_subreddit(value: str) -> bool:
    return bool(SUBREDDIT_RE.fullmatch(value))


def is_valid_post_id(value: str) -> bool:
    return bool(POST_ID_RE.fullmatch(value))
