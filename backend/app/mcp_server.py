"""Read-only MCP server exposing the intelligence store to analysts and
internal agents.

Deliberately narrow: search, single-object lookups, recent changes, related
CVEs, model releases and source evidence. NO generic SQL, no URL fetcher, no
file access, no write tools. Runs over streamable HTTP behind whatever
gateway/auth you put in front; per-tool authorisation and audit logging are
the gateway's job (the 2026 stateless-core spec makes method/tool names
visible to infrastructure for exactly this).
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

from mcp.server.fastmcp import FastMCP
from sqlalchemy import cast, desc, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import selectinload

from app.db import SessionLocal
from app.models import Entity, Event, EventEntity
from app.search.hybrid import hybrid_search

mcp = FastMCP("ai-news-intel", host="0.0.0.0", port=8100, streamable_http_path="/mcp")


@mcp.tool()
async def search_intelligence(query: str, taxonomy: str | None = None, days: int = 30, limit: int = 10) -> str:
    """Hybrid (lexical + semantic) search across all intelligence events."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    filters: dict = {"since": since}
    if taxonomy:
        filters["taxonomy"] = taxonomy
    async with SessionLocal() as db:
        results = await hybrid_search(db, query, filters=filters, limit=min(limit, 25))
    return json.dumps(results, default=str)


@mcp.tool()
async def get_event(event_id: str) -> str:
    """Fetch one event with entities and generated analyses."""
    async with SessionLocal() as db:
        stmt = (
            select(Event)
            .options(
                selectinload(Event.source),
                selectinload(Event.entities).selectinload(EventEntity.entity),
                selectinload(Event.analyses),
            )
            .where(Event.id == uuid.UUID(event_id))
        )
        event = (await db.execute(stmt)).scalar_one_or_none()
    if event is None:
        return json.dumps({"error": "not found"})
    from app.api.serializers import event_out

    return json.dumps(event_out(event, include_body=True), default=str)


@mcp.tool()
async def get_entity(entity_type: str, name: str) -> str:
    """Look up an entity (cve, model, repository, vendor, ...) by type+name."""
    async with SessionLocal() as db:
        entity = (
            await db.execute(
                select(Entity).where(
                    Entity.type == entity_type, Entity.canonical_name == name.strip().lower()
                )
            )
        ).scalar_one_or_none()
        if entity is None:
            return json.dumps({"error": "not found"})
    return json.dumps({"id": str(entity.id), "type": entity.type, "name": entity.name, "meta": entity.meta})


@mcp.tool()
async def get_recent_changes(entity_type: str, name: str, days: int = 7) -> str:
    """Recent events mentioning an entity — the 'what changed?' view."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    async with SessionLocal() as db:
        entity = (
            await db.execute(
                select(Entity).where(
                    Entity.type == entity_type, Entity.canonical_name == name.strip().lower()
                )
            )
        ).scalar_one_or_none()
        if entity is None:
            return json.dumps({"error": "entity not found"})
        rows = (
            await db.execute(
                select(Event)
                .join(EventEntity, EventEntity.event_id == Event.id)
                .where(EventEntity.entity_id == entity.id, Event.updated_at >= since)
                .order_by(desc(Event.updated_at))
                .limit(25)
            )
        ).scalars().all()
    return json.dumps(
        [
            {
                "id": str(e.id),
                "title": e.title,
                "version": e.version,
                "updated_at": e.updated_at.isoformat(),
                "priority_score": e.priority_score,
            }
            for e in rows
        ]
    )


@mcp.tool()
async def find_related_cves(product_or_keyword: str) -> str:
    """Find CVE-tagged events mentioning a product or keyword."""
    async with SessionLocal() as db:
        results = await hybrid_search(db, product_or_keyword, filters={"taxonomy": "offsec.vulnerability"}, limit=15)
    return json.dumps(results, default=str)


@mcp.tool()
async def find_model_releases(days: int = 30, limit: int = 15) -> str:
    """Model/inference releases in the window (ai.model.* / ai.inference)."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    async with SessionLocal() as db:
        rows = (
            await db.execute(
                select(Event)
                .where(
                    Event.published_at >= since,
                    # taxonomy is a JSON column: JSONB containment per label,
                    # OR'd for overlap semantics (ARRAY overlap doesn't exist here).
                    or_(
                        cast(Event.taxonomy, JSONB).contains([label])
                        for label in ("ai.model.release", "ai.model.weights", "ai.inference")
                    ),
                )
                .order_by(desc(Event.priority_score))
                .limit(min(limit, 25))
            )
        ).scalars().all()
    return json.dumps(
        [
            {
                "id": str(e.id),
                "title": e.title,
                "published_at": e.published_at.isoformat() if e.published_at else None,
                "taxonomy": e.taxonomy,
                "identifiers": e.identifiers,
                "priority_score": e.priority_score,
            }
            for e in rows
        ],
        default=str,
    )


@mcp.tool()
async def get_source_evidence(event_id: str) -> str:
    """Provenance for an event: source URL, raw object URI, hashes, version."""
    async with SessionLocal() as db:
        event = (
            await db.execute(
                select(Event).options(selectinload(Event.source)).where(Event.id == uuid.UUID(event_id))
            )
        ).scalar_one_or_none()
    if event is None:
        return json.dumps({"error": "not found"})
    return json.dumps(
        {
            "event_id": event_id,
            "source": event.source.slug if event.source else None,
            "source_url": event.source_url,
            "raw_object_uri": event.raw_object_uri,
            "content_hash": event.content_hash,
            "previous_content_hash": event.previous_content_hash,
            "version": event.version,
            "retrieved_at": event.retrieved_at.isoformat(),
        }
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
