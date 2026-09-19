"""SQLite cache for normalized Reddit posts."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.models.post import NormalizedPost

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id            TEXT PRIMARY KEY,
    subreddit     TEXT NOT NULL,
    title         TEXT NOT NULL,
    author        TEXT,
    original_url  TEXT NOT NULL,
    external_url  TEXT,
    thumbnail_url TEXT,
    body_html     TEXT,
    body_text     TEXT,
    categories    TEXT,
    created_at    TEXT NOT NULL,
    fetched_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_posts_subreddit_created
    ON posts (subreddit, created_at DESC);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def upsert_posts(self, posts: list[NormalizedPost]) -> int:
        """Insert posts, returning the number of newly discovered ones."""
        if not posts:
            return 0

        now = _utcnow().isoformat()
        with self._connect() as conn:
            existing = {
                row["id"]
                for row in conn.execute(
                    "SELECT id FROM posts WHERE subreddit = ?",
                    (posts[0].subreddit,),
                )
            }

            new_count = 0
            for post in posts:
                if post.id not in existing:
                    new_count += 1
                post.fetched_at = _utcnow()
                conn.execute(
                    """
                    INSERT INTO posts (
                        id, subreddit, title, author, original_url, external_url,
                        thumbnail_url, body_html, body_text, categories,
                        created_at, fetched_at
                    ) VALUES (
                        :id, :subreddit, :title, :author, :original_url, :external_url,
                        :thumbnail_url, :body_html, :body_text, :categories,
                        :created_at, :fetched_at
                    )
                    ON CONFLICT(id) DO UPDATE SET
                        subreddit     = excluded.subreddit,
                        title         = excluded.title,
                        author        = excluded.author,
                        original_url  = excluded.original_url,
                        external_url  = excluded.external_url,
                        thumbnail_url = excluded.thumbnail_url,
                        body_html     = excluded.body_html,
                        body_text     = excluded.body_text,
                        categories    = excluded.categories,
                        created_at    = excluded.created_at,
                        fetched_at    = excluded.fetched_at
                    """,
                    post.to_row(),
                )
            self._set_meta(conn, "last_refresh", now)
        return new_count

    def get_post(self, post_id: str) -> NormalizedPost | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        return NormalizedPost.from_row(row) if row else None

    def list_posts(self, subreddit: str, limit: int) -> list[NormalizedPost]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM posts
                WHERE subreddit = ? COLLATE NOCASE
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (subreddit, limit),
            ).fetchall()
        return [NormalizedPost.from_row(row) for row in rows]

    def count_posts(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM posts").fetchone()
        return int(row["n"])

    def get_meta(self, key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    @staticmethod
    def _set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
        conn.execute(
            """
            INSERT INTO meta (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
