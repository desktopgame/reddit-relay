"""Shared Jinja2 environment."""

from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.datetimeutil import to_rfc822

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)
_env.filters["rfc822"] = to_rfc822

templates = Jinja2Templates(env=_env)
