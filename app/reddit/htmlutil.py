"""Small HTML helpers for extracting and sanitizing Reddit content.

Reddit RSS embeds HTML inside the Atom ``content`` element.  We only need a
few well-known pieces (the self-text ``div.md`` block and the ``[link]``
anchor), so these helpers stay deliberately small instead of pulling in a full
DOM implementation.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

import nh3

REDDIT_BASE = "https://www.reddit.com"

_DIV_MD_RE = re.compile(r'<div\s+class="md">', re.IGNORECASE)
_DIV_TAG_RE = re.compile(r"<(/?)div\b[^>]*>", re.IGNORECASE)
_ANCHOR_RE = re.compile(r"<a\s+([^>]*)>(.*?)</a>", re.IGNORECASE | re.DOTALL)
_HREF_RE = re.compile(r'href\s*=\s*"([^"]*)"', re.IGNORECASE)
_RELATIVE_URL_RE = re.compile(r'(href|src)="(/[^"]*)"', re.IGNORECASE)

_ALLOWED_TAGS = {
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "del",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "sub",
    "sup",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}

_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title"},
}


def extract_selftext_html(content_html: str) -> str:
    """Return the inner HTML of the first ``div.md`` block, if present."""
    if not content_html:
        return ""
    match = _DIV_MD_RE.search(content_html)
    if not match:
        return ""

    start = match.end()
    depth = 1
    for tag in _DIV_TAG_RE.finditer(content_html, start):
        if tag.group(1) == "/":
            depth -= 1
            if depth == 0:
                return content_html[start : tag.start()]
        else:
            depth += 1
    return content_html[start:]


def find_anchor_href(html: str, text: str) -> str | None:
    """Find the ``href`` of the first anchor whose text equals ``text``."""
    if not html:
        return None
    for match in _ANCHOR_RE.finditer(html):
        anchor_text = strip_tags(match.group(2)).strip()
        if anchor_text == text:
            href = _HREF_RE.search(match.group(1))
            if href:
                return href.group(1)
    return None


def absolutize_reddit_urls(html: str) -> str:
    """Rewrite root-relative Reddit links to absolute reddit.com URLs."""
    if not html:
        return ""

    def replace(match: re.Match[str]) -> str:
        attr, path = match.group(1), match.group(2)
        return f'{attr}="{REDDIT_BASE}{path}"'

    return _RELATIVE_URL_RE.sub(replace, html)


def sanitize_html(html: str) -> str:
    """Sanitize Reddit-derived HTML before embedding it in our own page."""
    if not html:
        return ""
    return nh3.clean(
        absolutize_reddit_urls(html),
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes={"http", "https"},
        link_rel="noopener nofollow",
        strip_comments=True,
    )


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    @property
    def text(self) -> str:
        return "".join(self._parts)


def strip_tags(html: str) -> str:
    if not html:
        return ""
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # pragma: no cover - HTMLParser is tolerant, but be safe
        return html
    return re.sub(r"\s+", " ", parser.text).strip()
