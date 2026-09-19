"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - optional dependency
        return
    load_dotenv(PROJECT_ROOT / ".env")


def _get_str(key: str, default: str) -> str:
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _get_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    return int(raw.strip())


def _get_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    return float(raw.strip())


def _parse_subreddits(raw: str) -> tuple[str, ...]:
    seen: dict[str, str] = {}
    for part in raw.split(","):
        name = part.strip()
        if not name:
            continue
        seen.setdefault(name.lower(), name)
    return tuple(seen.values())


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    base_url: str
    db_path: Path
    subreddits: tuple[str, ...]
    refresh_interval_minutes: int
    refresh_stagger_seconds: float
    max_posts_per_subreddit: int
    user_agent: str
    request_timeout_seconds: float
    max_retries: int
    retry_delay_seconds: float
    log_level: str

    def subreddit_map(self) -> dict[str, str]:
        """Lower-cased subreddit name -> canonical configured name."""
        return {name.lower(): name for name in self.subreddits}

    def post_url(self, post_id: str) -> str:
        return f"{self.base_url.rstrip('/')}/post/{post_id}"

    def feed_url(self, subreddit: str) -> str:
        return f"{self.base_url.rstrip('/')}/feed/{subreddit}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_dotenv()

    db_raw = _get_str("REDDIT_RELAY_DB", "data/reddit-relay.db")
    db_path = Path(db_raw)
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path

    return Settings(
        host=_get_str("REDDIT_RELAY_HOST", "127.0.0.1"),
        port=_get_int("REDDIT_RELAY_PORT", 8080),
        base_url=_get_str("REDDIT_RELAY_BASE_URL", "http://127.0.0.1:8080"),
        db_path=db_path,
        subreddits=_parse_subreddits(_get_str("REDDIT_SUBREDDITS", "LocalLLaMA")),
        refresh_interval_minutes=max(1, _get_int("REDDIT_REFRESH_INTERVAL_MINUTES", 60)),
        refresh_stagger_seconds=max(0.0, _get_float("REDDIT_REFRESH_STAGGER_SECONDS", 30.0)),
        max_posts_per_subreddit=max(1, _get_int("REDDIT_MAX_POSTS_PER_SUBREDDIT", 50)),
        user_agent=_get_str("REDDIT_USER_AGENT", "reddit-relay/0.1 (personal Karakeep relay)"),
        request_timeout_seconds=_get_float("REDDIT_REQUEST_TIMEOUT_SECONDS", 20.0),
        max_retries=max(0, _get_int("REDDIT_MAX_RETRIES", 2)),
        retry_delay_seconds=max(0.0, _get_float("REDDIT_RETRY_DELAY_SECONDS", 60.0)),
        log_level=_get_str("REDDIT_RELAY_LOG_LEVEL", "INFO").upper(),
    )
