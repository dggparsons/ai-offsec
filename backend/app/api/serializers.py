"""Shared serializers for API responses."""

from app.models import Alert, Entity, Event, Source


def event_out(e: Event, include_body: bool = False) -> dict:
    out = {
        "id": str(e.id),
        "source": e.source.slug if e.source else None,
        "source_url": e.source_url,
        "source_type": e.source_type,
        "external_id": e.external_id,
        "title": e.title,
        "published_at": e.published_at.isoformat() if e.published_at else None,
        "modified_at": e.modified_at.isoformat() if e.modified_at else None,
        "taxonomy": e.taxonomy,
        "identifiers": e.identifiers,
        "priority_score": e.priority_score,
        "tldr": e.tldr,
        "score_components": e.score_components,
        "version": e.version,
        "is_novel": e.is_novel,
        "tlp": e.tlp,
        "entities": [
            {"type": link.entity.type, "name": link.entity.name, "role": link.role}
            for link in (e.entities or [])
            if link.entity
        ],
        "analyses": [
            {
                "kind": a.kind,
                "content": a.content,
                "confidence": a.confidence,
                "model": a.model,
                "prompt_version": a.prompt_version,
                "created_at": a.created_at.isoformat(),
            }
            for a in (e.analyses or [])
        ],
    }
    if include_body:
        out["body_text"] = e.body_text
        out["raw_object_uri"] = e.raw_object_uri
    return out


def source_out(s: Source) -> dict:
    return {
        "slug": s.slug,
        "name": s.name,
        "connector": s.connector,
        "url": s.url,
        "source_type": s.source_type,
        "priority": s.priority,
        "poll_interval_sec": s.poll_interval_sec,
        "trust_score": s.trust_score,
        "enabled": s.enabled,
        "last_fetched_at": s.last_fetched_at.isoformat() if s.last_fetched_at else None,
        "last_success_at": s.last_success_at.isoformat() if s.last_success_at else None,
        "consecutive_failures": s.consecutive_failures,
    }


def entity_out(e: Entity) -> dict:
    return {"id": str(e.id), "type": e.type, "name": e.name, "meta": e.meta}


def alert_out(a: Alert) -> dict:
    return {
        "id": str(a.id),
        "event_id": str(a.event_id),
        "severity": a.severity,
        "title": a.title,
        "body": a.body,
        "channel": a.channel,
        "delivered_at": a.delivered_at.isoformat() if a.delivered_at else None,
        "created_at": a.created_at.isoformat(),
    }
