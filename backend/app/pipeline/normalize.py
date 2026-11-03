"""Normalisation: hostile raw input -> safe plain text.

Raw bytes stay untouched in the object store. Everything the rest of the
pipeline (classifiers, LLMs, search indexers) sees passes through here:
HTML stripped, scripts/styles dropped, markdown reduced to prose, listing
boilerplate removed, whitespace collapsed, length-capped.
"""

import re

from bs4 import BeautifulSoup

MAX_BODY_CHARS = 50_000

_WS_RE = re.compile(r"[ \t]+")
_BLANK_RE = re.compile(r"\n{3,}")

_MD_STRIP_RE = re.compile(
    r"<[^>]+>"                      # HTML tags
    r"|!?\[([^\]]*)\]\([^)]*\)"     # markdown links/images -> keep text
    r"|^#{1,6}\s*"                  # heading markers at line start
    r"|^>{1,2}\s*"                  # blockquote markers at line start
    r"|&#x?[0-9a-fA-F]+;|&[a-z]+;",  # HTML entities
    re.M,
)
# Emphasis/code markers only count as markup at a word boundary — a bare
# run between word characters is an identifier (ACTION_SEND, file_name),
# not markdown (round-2: snake_case was being eaten into ACTIONSEND).
_EMPHASIS_RE = re.compile(r"(?<![\w])[*_`]{1,3}(?=\S)|(?<=\S)[*_`]{1,3}(?![\w])")
_BOILERPLATE_LINE_RE = re.compile(
    r"^\s*(article url|comments url|points|#?\s*comments|show hn|summary|impact|"
    r"executive summary|details|overview|description)\s*[:：]?\s*\S*\s*$",
    re.I,
)


def strip_markup(text: str) -> str:
    """Markdown/HTML remnants and listing boilerplate -> plain prose."""
    lines = [
        line
        for line in text.splitlines()
        if not _BOILERPLATE_LINE_RE.match(line) and not line.strip().startswith(("http://", "https://"))
    ]
    text = _MD_STRIP_RE.sub(lambda m: m.group(1) or "", "\n".join(lines))
    text = _EMPHASIS_RE.sub("", text)
    text = re.sub(r"(?im)^\s*tl;?dr\s*[:：-]?\s*", "", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def truncate_words(text: str, limit: int) -> str:
    """Word-boundary truncation with an ellipsis — never mid-word cuts."""
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    cut = cut[: cut.rfind(" ")] if " " in cut else cut
    return cut.rstrip(" ,;:") + "…"


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "iframe", "object", "embed"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return clean_text(text)


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = strip_markup(text)
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
