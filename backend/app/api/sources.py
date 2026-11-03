from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.serializers import source_out
from app.config import settings
from app.db import get_db
from app.models import Source

router = APIRouter(prefix="/api/sources", tags=["sources"])


class SourceIn(BaseModel):
    slug: str
    name: str
    connector: str
    url: str
    source_type: str = "other"
    priority: str = "P2"
    poll_interval_sec: int = 3600
    trust_score: float = 0.5
    tlp: str = "CLEAR"
    licence: str = ""
    allow_external_llm: bool = False
    config: dict = {}


@router.get("")
async def list_sources(db: AsyncSession = Depends(get_db)):
    sources = (await db.execute(select(Source).order_by(Source.priority, Source.name))).scalars().all()
    return [source_out(s) for s in sources]


@router.post("", status_code=201)
async def create_source(payload: SourceIn, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Source).where(Source.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "source slug already exists")
    source = Source(**payload.model_dump())
    db.add(source)
    await db.commit()
    return source_out(source)


@router.patch("/{slug}")
async def update_source(slug: str, patch: dict, db: AsyncSession = Depends(get_db)):
    source = (await db.execute(select(Source).where(Source.slug == slug))).scalar_one_or_none()
    if source is None:
        raise HTTPException(404, "source not found")
    allowed = {"enabled", "poll_interval_sec", "trust_score", "priority", "config", "allow_external_llm", "licence", "tlp"}
    for key, value in patch.items():
        if key in allowed:
            setattr(source, key, value)
    await db.commit()
    return source_out(source)


@router.post("/{slug}/fetch", status_code=202)
async def fetch_now(slug: str, db: AsyncSession = Depends(get_db)):
    source = (await db.execute(select(Source).where(Source.slug == slug))).scalar_one_or_none()
    if source is None:
        raise HTTPException(404, "source not found")
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    await redis.enqueue_job("fetch_source", slug)
    return {"status": "enqueued", "source": slug}
