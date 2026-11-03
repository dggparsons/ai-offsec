"""arq worker: scheduler sweep + fetch/process jobs.

The sweep enqueues a `fetch_source` job for every enabled source whose
poll interval has elapsed. Fetch jobs run connectors, hand envelopes to the
ingest pipeline, and maintain per-source health (last success, consecutive
failures, validator cursors). A connector that keeps failing backs off by
temporarily stretching its own poll interval.
"""

import logging
from datetime import datetime, timezone

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select

from app.config import settings
from app.connectors.base import build_connector
from app.db import SessionLocal, engine
from app.models import Base, Event, Source
from app.pipeline import llm as llm_mod
from app.pipeline import score as scorer
from app.pipeline.ingest import process_envelope

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("worker")


async def fetch_source(ctx, slug: str) -> dict:
    async with SessionLocal() as db:
        source = (await db.execute(select(Source).where(Source.slug == slug))).scalar_one_or_none()
        if source is None or not source.enabled:
            return {"status": "skipped", "reason": "missing or disabled"}

        connector = build_connector(source)
        source.last_fetched_at = datetime.now(timezone.utc)
        try:
            envelopes, validators = await connector.fetch()
        except Exception as exc:
            source.consecutive_failures += 1
            await db.commit()
            log.exception("fetch failed for %s", slug)
            return {"status": "error", "error": str(exc)}

        if etag := validators.get("etag"):
            source.etag = etag
        if lm := validators.get("last_modified"):
            source.last_modified_header = lm

        results = {"created": 0, "updated": 0, "unchanged": 0, "failed": 0}
        for env in envelopes:
            try:
                outcome = await process_envelope(db, source, env)
                results[outcome["status"]] = results.get(outcome["status"], 0) + 1
                # Commit per envelope: a large fetch with LLM analysis can
                # hit the job timeout mid-loop, and committed work survives
                # (next poll fast-paths those as "unchanged" and resumes).
                await db.commit()
            except Exception:
                log.exception("failed to process envelope %s from %s", env.external_id, slug)
                await db.rollback()
                results["failed"] += 1
                continue

        # Honest health: a fetch where every envelope failed to process is a
        # failure, not a success (round-1 standards fix). Partial failures
        # are logged and reported but still count as a successful cycle.
        if envelopes and results["failed"] == len(envelopes):
            source.consecutive_failures += 1
            await db.commit()
            log.error("source %s: all %d envelopes failed processing", slug, len(envelopes))
            return {"status": "error", **results}
        if results["failed"]:
            log.warning("source %s: %d/%d envelopes failed", slug, results["failed"], len(envelopes))
        source.last_success_at = datetime.now(timezone.utc)
        source.consecutive_failures = 0
        await db.commit()
        log.info("source %s: %s", slug, results)
        return {"status": "ok", **results}


async def sweep_due_sources(ctx) -> dict:
    """Enqueue fetches for sources whose poll interval has elapsed."""
    now = datetime.now(timezone.utc)
    async with SessionLocal() as db:
        sources = (await db.execute(select(Source).where(Source.enabled))).scalars().all()
        due = []
        for s in sources:
            if s.last_fetched_at is None:
                due.append(s.slug)
                continue
            last = s.last_fetched_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            # Back-off: each consecutive failure doubles the effective interval (x8 max).
            effective = s.poll_interval_sec * (2 ** min(s.consecutive_failures, 3))
            if (now - last).total_seconds() >= effective:
                due.append(s.slug)

    enqueued = []
    for slug in due:
        await ctx["redis"].enqueue_job("fetch_source", slug)
        enqueued.append(slug)
    if enqueued:
        log.info("enqueued %d sources: %s", len(enqueued), enqueued)
    return {"enqueued": enqueued}


async def generate_daily_digest(ctx) -> dict:
    """Snapshot today's digest into the digests table (daily archive)."""
    from app.api.digest import snapshot_today

    async with SessionLocal() as db:
        content = await snapshot_today(db)
    log.info("digest snapshot: %s actionable, %s material", content["items_requiring_action"], content["material_developments"])
    return {"status": "ok", "actionable": content["items_requiring_action"]}


async def rescore_events(ctx) -> dict:
    """Maintenance: re-classify, re-gate, re-score and re-TLDR every event
    under the current pipeline rules (heuristic only, no LLM calls), and
    delete the filler analysis rows the old heuristic path used to write.
    Idempotent; runs on worker startup so pipeline changes propagate to the
    back catalogue. Events with a real LLM analysis keep their TLDR."""
    from sqlalchemy import delete as sa_delete
    from sqlalchemy.orm import selectinload

    from app.models import Analysis
    from app.pipeline.classify import ALLOWED_LABELS, classify, is_ai_relevant
    from app.pipeline.normalize import clean_text
    from app.search.hybrid import SEARCH_VECTOR_SQL

    rescored = 0
    async with SessionLocal() as db:
        # Drop all heuristic-mode analysis rows: they were filler ("Automated
        # delta unavailable...") or verbatim copies of the body, not analysis.
        await db.execute(sa_delete(Analysis).where(Analysis.model == "heuristic"))
        events = (
            await db.execute(
                select(Event).options(selectinload(Event.source), selectinload(Event.analyses))
            )
        ).scalars().all()
        for e in events:
            # Retitle raw release tags left by the pre-fix releases
            # connector ("ggml-org/llama.cpp b12077: b12077", also the
            # "tag: name" form where name is just a prefix of the tag).
            if e.source_type in ("repository_release", "specification"):
                import re

                m = re.match(r"^(\S+)/(\S+)\s+(\S+):\s*(\S*)$", e.title or "")
                if m:
                    _org, project, tag, name = m.groups()
                    if not name or tag.startswith(name) or name.startswith(tag):
                        e.title = f"{project} release {tag}"
            # Re-clean the stored body under current normalisation rules
            # (markdown/boilerplate stripping) and keep the FTS index in step.
            cleaned = clean_text(e.body_text or "")
            if cleaned != (e.body_text or ""):
                e.body_text = cleaned
                await db.execute(SEARCH_VECTOR_SQL, {"event_id": e.id})
            text = f"{e.title or ''}\n{e.body_text or ''}"
            has_llm_analysis = any(a.model != "heuristic" for a in (e.analyses or []))
            heuristic_labels = classify(text)
            if has_llm_analysis:
                # Keep labels the LLM contributed (round-2: rescore used to
                # erase them, fighting ingest's merge); they were validated
                # against ALLOWED_LABELS when written.
                keep = {t for t in (e.taxonomy or []) if t in ALLOWED_LABELS}
                e.taxonomy = sorted(set(heuristic_labels) | keep)
            else:
                e.taxonomy = heuristic_labels
            e.ai_relevant = is_ai_relevant(text, e.taxonomy, e.source_type)
            components = e.score_components or {}
            priority, components = scorer.score_event(
                source_authority=e.source.trust_score if e.source else e.source_confidence,
                taxonomy=e.taxonomy,
                identifiers=e.identifiers or {},
                body=e.body_text or "",
                published_at=e.published_at,
                is_novel=e.is_novel,
                corroborated=(components.get("corroboration", 0) or 0) >= 1,
                source_type=e.source_type,
                ai_relevant=e.ai_relevant,
            )
            e.priority_score = priority
            e.score_components = components
            if not has_llm_analysis:
                e.tldr = llm_mod.make_tldr(e.title or "", e.body_text or "")
            rescored += 1
        await db.commit()
    log.info("rescore: %d events reprocessed", rescored)
    return {"rescored": rescored}


async def startup(ctx):
    # Worker owns schema creation when it beats the API to boot.
    async with engine.begin() as conn:
        from sqlalchemy import text

        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text("ALTER TABLE events ADD COLUMN IF NOT EXISTS ai_relevant BOOLEAN DEFAULT FALSE")
        )
    import asyncio

    from app.db import ensure_bucket

    await asyncio.to_thread(ensure_bucket)
    # Kick off an immediate first sweep so fresh installs ingest right away.
    await ctx["redis"].enqueue_job("sweep_due_sources")
    await ctx["redis"].enqueue_job("rescore_events")


async def shutdown(ctx):
    await engine.dispose()


class WorkerSettings:
    functions = [fetch_source, sweep_due_sources, generate_daily_digest, rescore_events]
    cron_jobs = [
        cron(sweep_due_sources, second={0}),       # sweep once per minute
        cron(generate_daily_digest, hour={7}, minute={3}),  # daily snapshot, 07:03 UTC
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 8
    job_timeout = 600
