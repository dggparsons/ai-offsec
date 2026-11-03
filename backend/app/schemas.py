"""Canonical ingestion envelope.

Every connector, regardless of source type, produces these objects. Raw bytes
are stored separately in the object store; this envelope carries extracted
text and metadata into the pipeline. Do not collapse source data straight
into an LLM summary — this schema is the auditable intermediate form.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Identifiers(BaseModel):
    cve: list[str] = Field(default_factory=list)
    ghsa: list[str] = Field(default_factory=list)
    cwe: list[str] = Field(default_factory=list)
    repository: list[str] = Field(default_factory=list)
    model: list[str] = Field(default_factory=list)
    arxiv: list[str] = Field(default_factory=list)
    other: dict[str, Any] = Field(default_factory=dict)


class CanonicalEnvelope(BaseModel):
    source_id: str  # source registry slug
    source_url: str
    source_type: str = "other"
    external_id: str | None = None  # stable ID at the origin (CVE id, GHSA id, guid...)

    retrieved_at: datetime | None = None
    published_at: datetime | None = None
    modified_at: datetime | None = None

    language: str = "en"
    title: str = ""
    body_text: str = ""
    author: str = ""

    # Raw bytes as fetched; the pipeline hashes and stores them immutably,
    # then clears this field before the envelope leaves the ingestion edge.
    raw_content: bytes | None = None
    raw_content_type: str = "text/html"

    entities: list[dict[str, str]] = Field(default_factory=list)  # [{"type": "cve", "name": "..."}]
    identifiers: Identifiers = Field(default_factory=Identifiers)
    taxonomy: list[str] = Field(default_factory=list)

    source_confidence: float = 0.5
    tlp: str = "CLEAR"
    licence: str = ""
