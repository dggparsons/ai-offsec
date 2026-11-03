"""Ingest orchestrator: envelope -> stored, scored, analysed, indexed event.

Ordering matters: raw evidence is persisted immutably BEFORE any derived
processing, so every conclusion is auditable back to source bytes.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_s3
from app.models import Alert, Analysis, Entity, Event, EventEntity, Source
from app.pipeline import alerts, dedupe, embed, extract, llm, normalize, score
from app.schemas import CanonicalEnvelope
from app.search.hybrid import SEARCH_VECTOR_SQL

log = logging.getLogger(__name__)


def store_raw(content: bytes, content_hash: str, content_type: str) -> str:
    """Immutable raw object store. Keyed by content hash: identical bytes
    are stored once, forever."""
    key = f"raw/{content_hash[:2]}/{content_hash}"
    s3 = get_s3()
    try:
        s3.head_object(Bucket=settings.s3_bucket, Key=key)
    except Exception:
        s3.put_object(Bucket=settings.s3_bucket, Key=key, Body=content, ContentType=content_type)
    return f"s3://{settings.s3_bucket}/{key}"


async def upsert_entity(db: AsyncSession, type_: str, name: str) -> Entity:
    canonical = name.strip().lower()
    q = await db.execute(select(Entity).where(Entity.type == type_, Entity.canonical_name == canonical))
    if entity := q.scalar_one_or_none():
        return entity
    entity = Entity(type=type_, name=name.strip(), canonical_name=canonical)
    try:
        # Savepoint so a concurrent job inserting the same entity only loses
        # the race, not the whole surrounding transaction.
        async with db.begin_nested():
            db.add(entity)
            await db.flush()
    except IntegrityError:
        db.expunge(entity)
        entity = (
            await db.execute(
                select(Entity).where(Entity.type == type_, Entity.canonical_name == canonical)
            )
        ).scalar_one()
    return entity


async def process_envelope(db: AsyncSession, source: Source, env: CanonicalEnvelope) -> dict:
    raw = env.raw_content or (env.title + "\n\n" + env.body_text).encode()
    content_hash = dedupe.sha256_hex(raw)
    body = normalize.normalize_body(env.body_text, env.raw_content_type)
    norm_hash = dedupe.normalized_hash(env.title, body)

    identifiers = extract.extract_identifiers(
        f"{env.title}\n{body}", existing=env.identifiers.model_dump()
    )

    existing = await dedupe.find_existing_event(db, source.id, env.external_id, identifiers)

    if existing and existing.content_hash == content_hash:
        return {"status": "unchanged", "event_id": str(existing.id)}

    corroborated = bool(existing and str(existing.source_id) != str(source.id))
    is_novel = existing is None

    if existing is None:
        event = Event(
            source_id=source.id,
            source_url=env.source_url,
            source_type=env.source_type,
            external_id=env.external_id,
            published_at=env.published_at,
            modified_at=env.modified_at,
            title=env.title[:4000],
            author=env.author[:512],
            content_hash=content_hash,
            normalized_hash=norm_hash,
            raw_object_uri=store_raw(raw, content_hash, env.raw_content_type),
            tlp=env.tlp,
        )
        db.add(event)
        await db.flush()
    else:
        event = existing
        # Versioned object: bump and chain hashes so change history is explicit.
        event.version += 1
        event.previous_content_hash = event.content_hash
        event.content_hash = content_hash
        event.normalized_hash = norm_hash
        event.raw_object_uri = store_raw(raw, content_hash, env.raw_content_type)
        event.modified_at = env.modified_at or datetime.now(timezone.utc)
        if corroborated:
            event.source_confidence = min(1.0, event.source_confidence + 0.1)

    event.body_text = body
    event.title = env.title[:4000] or event.title
    event.published_at = env.published_at or event.published_at
    event.identifiers = identifiers

    taxonomy = normalize_taxonomy(env.taxonomy, env.title, body)
    event.taxonomy = taxonomy

    priority, components = score.score_event(
        source_authority=source.trust_score,
        taxonomy=taxonomy,
        identifiers=identifiers,
        body=body,
        published_at=event.published_at,
        is_novel=is_novel,
        corroborated=corroborated,
        source_type=env.source_type,
    )
    event.priority_score = priority
    event.score_components = components
    event.is_novel = is_novel
    event.processing_version = settings.processing_version

    # Entities (deterministic extraction only at this stage). Query existing
    # links explicitly — touching event.entities here would lazy-load, which
    # async SQLAlchemy forbids.
    linked = set(
        (await db.execute(select(EventEntity.entity_id).where(EventEntity.event_id == event.id)))
        .scalars()
        .all()
    )
    for ent in extract.identifiers_to_entities(identifiers):
        entity = await upsert_entity(db, ent["type"], ent["name"])
        if entity.id not in linked:
            db.add(EventEntity(event_id=event.id, entity_id=entity.id))
            linked.add(entity.id)

    # Analysis: only on new events or real content change (normalised hash).
    changed = is_novel or event.previous_content_hash != event.content_hash
    if changed:
        vector, _embed_model = await embed.embed_text(f"{event.title}\n\n{body[:4000]}")
        event.embedding = vector

        if source.allow_external_llm or _endpoint_is_local():
            analysis, model_label = await llm.llm_analysis(event.title, body)
        else:
            analysis, model_label = llm.heuristic_analysis(event.title, body, taxonomy)
        event.tldr = str(analysis.pop("tldr", "") or llm.make_tldr(event.title, body))[:400]
        merged_labels = sorted(set(taxonomy) | set(analysis.pop("taxonomy_labels", []) or []))
        event.taxonomy = merged_labels
        confidence = analysis.pop("confidence", "low")
        for kind, content in analysis.items():
            text = "\n".join(content) if isinstance(content, list) else str(content)
            if not text or text == "None identified.":
                continue
            db.add(
                Analysis(
                    event_id=event.id,
                    kind=kind,
                    content=text[:8000],
                    confidence=confidence,
                    evidence_event_ids=[str(event.id)],
                    model=model_label,
                    prompt_version=llm.PROMPT_VERSION,
                )
            )

    # Alerts on high-priority new/changed events.
    if priority >= settings.alert_threshold and changed:
        severity = score.severity_for(priority, event.taxonomy)
        title = f"[{severity.upper()}] {event.title[:160]}"
        alert_body = _alert_body(event, components)
        alert = Alert(event_id=event.id, severity=severity, title=title, body=alert_body)
        db.add(alert)
        await db.flush()
        channel = "queued"
        if await alerts.deliver_slack(title, alert_body):
            channel = "slack"
        elif await alerts.deliver_email(title, alert_body):
            channel = "email"
        if channel != "queued":
            alert.channel = channel
            alert.delivered_at = datetime.now(timezone.utc)

    await db.flush()
    await db.execute(SEARCH_VECTOR_SQL, {"event_id": event.id})
    return {
        "status": "created" if is_novel else "updated",
        "event_id": str(event.id),
        "priority": priority,
        "corroborated": corroborated,
    }


def normalize_taxonomy(initial: list[str], title: str, body: str) -> list[str]:
    from app.pipeline.classify import classify

    return classify(f"{title}\n{body}", existing=initial)


def _endpoint_is_local() -> bool:
    return any(
        host in settings.llm_base_url
        for host in ("localhost", "127.0.0.1", "host.docker.internal", "ollama")
    )


def _alert_body(event: Event, components: dict) -> str:
    ids = event.identifiers or {}
    evidence = [event.source_url]
    return (
        f"Entity: {', '.join(ids.get('cve', []) + ids.get('model', [])) or event.title[:80]}\n"
        f"Why now: priority {event.priority_score:.2f}; "
        f"top signals: {_top_components(components)}\n"
        f"Taxonomy: {', '.join(event.taxonomy[:6])}\n"
        f"Evidence: {' · '.join(evidence)}\n"
        f"First seen: {event.created_at.isoformat()} · Version: {event.version}"
    )


def _top_components(components: dict, n: int = 3) -> str:
    top = sorted(components.items(), key=lambda kv: kv[1], reverse=True)[:n]
    return ", ".join(f"{k}={v:.2f}" for k, v in top)
