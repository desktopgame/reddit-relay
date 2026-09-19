"""Parse Reddit's Atom feeds into :class:`NormalizedPost` objects."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime

from app.models.post import NormalizedPost
from app.reddit.htmlutil import (
    extract_selftext_html,
    find_anchor_href,
    sanitize_html,
    strip_tags,
)

ATOM = "{http://www.w3.org/2005/Atom}"
MEDIA = "{http://search.yahoo.com/mrss/}"


def _text(element: ET.Element | None) -> str:
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def _parse_datetime(raw: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return datetime.now(UTC)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _parse_entry(entry: ET.Element, subreddit: str) -> NormalizedPost | None:
    post_id = _text(entry.find(f"{ATOM}id"))
    title = _text(entry.find(f"{ATOM}title"))
    link_el = entry.find(f"{ATOM}link")
    original_url = link_el.get("href", "") if link_el is not None else ""
    if not post_id or not original_url:
        return None

    author = _text(entry.find(f"{ATOM}author/{ATOM}name"))
    if author.startswith("/u/"):
        author = author[3:]
    elif author.startswith("u/"):
        author = author[2:]

    created_raw = _text(entry.find(f"{ATOM}published")) or _text(entry.find(f"{ATOM}updated"))

    content_el = entry.find(f"{ATOM}content")
    content_html = content_el.text or "" if content_el is not None else ""

    selftext_html = sanitize_html(extract_selftext_html(content_html))
    selftext = strip_tags(selftext_html)

    external_url = find_anchor_href(content_html, "[link]")
    if external_url == original_url:
        external_url = None

    thumbnail_el = entry.find(f"{MEDIA}thumbnail")
    thumbnail_url = thumbnail_el.get("url") if thumbnail_el is not None else None

    categories = tuple(
        term
        for term in (
            category.get("term", "").strip() for category in entry.findall(f"{ATOM}category")
        )
        if term
    )

    return NormalizedPost(
        id=post_id,
        subreddit=subreddit,
        title=title,
        author=author,
        original_url=original_url,
        created_at=_parse_datetime(created_raw),
        selftext=selftext,
        selftext_html=selftext_html,
        external_url=external_url,
        thumbnail_url=thumbnail_url,
        categories=categories,
    )


def parse_atom_feed(content: bytes, subreddit: str) -> list[NormalizedPost]:
    root = ET.fromstring(content)
    posts: list[NormalizedPost] = []
    for entry in root.findall(f"{ATOM}entry"):
        post = _parse_entry(entry, subreddit)
        if post is not None:
            posts.append(post)
    return posts


def parse_single_entry(content: bytes, subreddit: str) -> NormalizedPost | None:
    root = ET.fromstring(content)
    entry = root.find(f"{ATOM}entry")
    if entry is None:
        return None
    return _parse_entry(entry, subreddit)
