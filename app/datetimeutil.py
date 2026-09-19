"""Date formatting helpers for feed rendering."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import format_datetime


def to_rfc822(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return format_datetime(value.astimezone(UTC))
