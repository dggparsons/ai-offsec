import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text

from app.config import settings
from app.db import SessionLocal, engine, ensure_bucket
from app.models import Base, Event, Source

log = logging.getLogger(__name__)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        # create_all never alters existing tables — additive migrations here.
        await conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS tldr TEXT DEFAULT ''"))
        await conn.execute(
            text("ALTER TABLE events ADD COLUMN IF NOT EXISTS ai_relevant BOOLEAN DEFAULT FALSE")
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS events_search_idx ON events USING gin(search_vector)"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS events_embedding_idx "
                "ON events USING hnsw (embedding vector_cosine_ops)"
            )
        )


async def seed_sources() -> None:
    """Sync the seed registry into the sources table: insert new slugs and
    correct a seed's URL when it changes upstream (round-1: arXiv's legacy
    host, Google Security Blog's move to blog.google). Runtime state (etags,
    cursors, failure counts) and operator edits to cadence/trust are never
    touched."""
    from app.connectors.seeds import SEED_SOURCES

    async with SessionLocal() as db:
        existing = {s.slug: s for s in (await db.execute(select(Source))).scalars().all()}
        added = updated = 0
        for data in SEED_SOURCES:
            row = existing.get(data["slug"])
            if row is None:
                db.add(Source(**data))
                added += 1
            elif row.url != data["url"]:
                log.info("seed sync: %s url %s -> %s", data["slug"], row.url, data["url"])
                row.url = data["url"]
                row.etag = None  # validators belong to the old endpoint
                row.last_modified_header = None
                updated += 1
        await db.commit()
        if added or updated:
            log.info("seed sync: %d added, %d url-corrected", added, updated)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await asyncio.to_thread(ensure_bucket)
    await seed_sources()
    yield
    await engine.dispose()


app = FastAPI(
    title="AI News Intelligence",
    version=settings.processing_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)

# Write guard: every mutating request requires the API write key. Fail closed —
# with no key configured, all writes are denied. Reads stay public by design.
@app.middleware("http")
async def guard_writes_and_headers(request: Request, call_next):
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if not settings.api_write_key or request.headers.get("x-api-key") != settings.api_write_key:
            return JSONResponse({"detail": "write access denied"}, status_code=403)
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return resp

from app.api import alerts, digest, entities, events, feedback, search, sources  # noqa: E402

for r in (events.router, search.router, sources.router, entities.router, alerts.router, digest.router, feedback.router):
    app.include_router(r)


@app.get("/api/health")
async def health():
    async with SessionLocal() as db:
        event_count = await db.scalar(select(func.count()).select_from(Event))
        source_count = await db.scalar(select(func.count()).select_from(Source).where(Source.enabled))
    return {"status": "ok", "events": event_count, "enabled_sources": source_count}
