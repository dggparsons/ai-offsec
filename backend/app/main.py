import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text

from app.config import settings
from app.db import SessionLocal, engine, ensure_bucket
from app.models import Base, Event, Source

log = logging.getLogger(__name__)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
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
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import alerts, digest, entities, events, feedback, search, sources  # noqa: E402

for r in (events.router, search.router, sources.router, entities.router, alerts.router, digest.router, feedback.router):
    app.include_router(r)


@app.get("/api/health")
async def health():
    async with SessionLocal() as db:
        event_count = await db.scalar(select(func.count()).select_from(Event))
        source_count = await db.scalar(select(func.count()).select_from(Source).where(Source.enabled))
    return {"status": "ok", "events": event_count, "enabled_sources": source_count}
