import logging
import asyncio
import os
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
    from app.connectors.seeds import SEED_SOURCES

    async with SessionLocal() as db:
        existing = await db.scalar(select(func.count()).select_from(Source))
        if existing:
            return
        for data in SEED_SOURCES:
            db.add(Source(**data))
        await db.commit()
        log.info("seeded %d sources", len(SEED_SOURCES))


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
API_WRITE_KEY = os.environ.get("API_WRITE_KEY", "")


@app.middleware("http")
async def guard_writes_and_headers(request: Request, call_next):
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if not API_WRITE_KEY or request.headers.get("x-api-key") != API_WRITE_KEY:
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
