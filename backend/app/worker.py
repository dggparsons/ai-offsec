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
from app.models import Base, Source
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

        results = {"created": 0, "updated": 0, "unchanged": 0}
        for env in envelopes:
            try:
                outcome = await process_envelope(db, source, env)
                results[outcome["status"]] = results.get(outcome["status"], 0) + 1
            except Exception:
                log.exception("failed to process envelope %s from %s", env.external_id, slug)
                await db.rollback()
                continue

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


async def startup(ctx):
    # Worker owns schema creation when it beats the API to boot.
    async with engine.begin() as conn:
        from sqlalchemy import text

        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    import asyncio

    from app.db import ensure_bucket

    await asyncio.to_thread(ensure_bucket)
    # Kick off an immediate first sweep so fresh installs ingest right away.
    await ctx["redis"].enqueue_job("sweep_due_sources")


async def shutdown(ctx):
    await engine.dispose()


class WorkerSettings:
    functions = [fetch_source, sweep_due_sources]
    cron_jobs = [cron(sweep_due_sources, second={0})]  # sweep once per minute
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 8
    job_timeout = 600
