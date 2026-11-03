"""Normalisation: hostile raw input -> safe plain text.

Raw bytes stay untouched in the object store. Everything the rest of the
pipeline (classifiers, LLMs, search indexers) sees passes through here:
HTML stripped, scripts/styles dropped, whitespace collapsed, length-capped.
"""

import re

from bs4 import BeautifulSoup

MAX_BODY_CHARS = 50_000

_WS_RE = re.compile(r"[ \t]+")
_BLANK_RE = re.compile(r"\n{3,}")


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "iframe", "object", "embed"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return clean_text(text)


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [_WS_RE.sub(" ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = _BLANK_RE.sub("\n\n", text).strip()
    return text[:MAX_BODY_CHARS]


def normalize_body(body: str, content_type: str) -> str:
    if "html" in content_type or body.lstrip().lower().startswith(("<!doctype", "<html")):
        return html_to_text(body)
    return clean_text(body)


def normalized_hash_input(title: str, body: str) -> str:
    """Formatting-insensitive form for near-duplicate hashing: lowercase,
    alphanumerics only. Catches template-only changes between fetches."""
    return re.sub(r"[^a-z0-9]", "", (title + " " + body).lower())
