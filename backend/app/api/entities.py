import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.serializers import entity_out, event_out
from app.db import get_db
from app.models import Entity, Event, EventEntity

router = APIRouter(prefix="/api/entities", tags=["entities"])


@router.get("")
async def list_entities(
    db: AsyncSession = Depends(get_db),
    type: str | None = None,
    q: str | None = None,
    limit: int = Query(50, le=200),
):
    stmt = select(Entity).limit(limit)
    if type:
        stmt = stmt.where(Entity.type == type)
    if q:
        stmt = stmt.where(Entity.name.ilike(f"%{q}%"))
    entities = (await db.execute(stmt.order_by(Entity.type, Entity.name))).scalars().all()
    return [entity_out(e) for e in entities]


@router.get("/{entity_id}")
async def get_entity(entity_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    entity = (await db.execute(select(Entity).where(Entity.id == entity_id))).scalar_one_or_none()
    if entity is None:
        raise HTTPException(404, "entity not found")
    links = (
        await db.execute(
            select(EventEntity)
            .join(Event, EventEntity.event_id == Event.id)
            .options(
                selectinload(EventEntity.event).selectinload(Event.source),
                selectinload(EventEntity.event).selectinload(Event.entities).selectinload(EventEntity.entity),
                selectinload(EventEntity.event).selectinload(Event.analyses),
            )
            .where(EventEntity.entity_id == entity.id)
            .order_by(desc(Event.published_at))
            .limit(50)
        )
    ).scalars().all()
    return {
        **entity_out(entity),
        "event_count": await db.scalar(
            select(func.count()).select_from(EventEntity).where(EventEntity.entity_id == entity.id)
        ),
        "recent_events": [event_out(link.event) for link in links],
    }
