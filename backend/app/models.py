import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Source(Base):
    """Source registry entry. Also carries per-source collection policy:
    licence/terms notes, whether content may be sent to external models,
    and connector-specific config (feed URL, repo list, API params)."""

    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    connector: Mapped[str] = mapped_column(String(64))  # registry key, e.g. "rss", "cisa_kev"
    url: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(64), default="other")
    priority: Mapped[str] = mapped_column(String(8), default="P2")  # P0 / P0-P1 / P1 / P2
    poll_interval_sec: Mapped[int] = mapped_column(Integer, default=3600)
    trust_score: Mapped[float] = mapped_column(Float, default=0.5)  # 0..1 source authority
    tlp: Mapped[str] = mapped_column(String(16), default="CLEAR")
    licence: Mapped[str] = mapped_column(Text, default="")
    allow_external_llm: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    etag: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_modified_header: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)

    events: Mapped[list["Event"]] = relationship(back_populates="source")


class Event(Base):
    """Canonical event. Re-fetching the same advisory updates this row and
    bumps `version`; previous raw bytes remain in the object store, and
    `previous_content_hash` chains versions for change detection."""

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str | None] = mapped_column(String(512), index=True, nullable=True)

    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    language: Mapped[str] = mapped_column(String(8), default="en")
    title: Mapped[str] = mapped_column(Text, default="")
    body_text: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str] = mapped_column(String(512), default="")

    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    normalized_hash: Mapped[str] = mapped_column(String(64), index=True)
    previous_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_object_uri: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)

    identifiers: Mapped[dict] = mapped_column(JSON, default=dict)
    taxonomy: Mapped[list] = mapped_column(JSON, default=list)
    source_confidence: Mapped[float] = mapped_column(Float, default=0.5)
    tlp: Mapped[str] = mapped_column(String(16), default="CLEAR")
    processing_version: Mapped[str] = mapped_column(String(32), default="")

    # Relevance scoring breakdown; `priority_score` is the headline number.
    score_components: Mapped[dict] = mapped_column(JSON, default=dict)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    is_novel: Mapped[bool] = mapped_column(Boolean, default=True)

    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embed_dim), nullable=True)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    source: Mapped[Source] = relationship(back_populates="events")
    entities: Mapped[list["EventEntity"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="event", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_event_source_external"),)


class Entity(Base):
    """Explicit entities: vendor, organisation, model, model_family,
    repository, product, cve, ghsa, cwe, exploit, paper, author, conference,
    framework, mcp_server, mcp_client, enterprise_deployment."""

    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(512), index=True)
    canonical_name: Mapped[str] = mapped_column(String(512), index=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    events: Mapped[list["EventEntity"]] = relationship(back_populates="entity", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("type", "canonical_name", name="uq_entity_type_name"),)


class EventEntity(Base):
    __tablename__ = "event_entities"

    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(64), default="mentioned")  # mentioned / affects / released_by ...

    event: Mapped[Event] = relationship(back_populates="entities")
    entity: Mapped[Entity] = relationship(back_populates="events")


class Analysis(Base):
    """LLM- or heuristic-generated assessment. Always traceable: stores the
    model, prompt version and the source event IDs used as evidence. Never
    overwrite — new model/prompt versions insert new rows."""

    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(64))  # fact_summary | technical_delta | offensive_significance | ...
    content: Mapped[str] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(16), default="low")  # high / medium / low
    evidence_event_ids: Mapped[list] = mapped_column(JSON, default=list)
    model: Mapped[str] = mapped_column(String(128), default="heuristic")
    prompt_version: Mapped[str] = mapped_column(String(32), default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    event: Mapped[Event] = relationship(back_populates="analyses")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium")  # critical / high / medium / low
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(32), default="queued")  # queued / slack / email
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Feedback(Base):
    """Analyst actions — the future training signal for learned relevance."""

    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    analyst: Mapped[str] = mapped_column(String(128), default="anonymous")
    action: Mapped[str] = mapped_column(String(32))  # open / save / escalate / dismiss / important
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
