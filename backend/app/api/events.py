import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.serializers import event_out
from app.db import get_db
from app.models import Event, EventEntity

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("")
async def list_events(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = 0,
    taxonomy: str | None = None,
    source_type: str | None = None,
    min_priority: float | None = None,
    since: datetime | None = None,
    order: str = "published",
):
    stmt = (
        select(Event)
        .options(
            selectinload(Event.source),
            selectinload(Event.entities).selectinload(EventEntity.entity),
            selectinload(Event.analyses),
        )
        .offset(offset)
        .limit(limit)
    )
    if taxonomy:
        stmt = stmt.where(Event.taxonomy.contains([taxonomy]))
    if source_type:
        stmt = stmt.where(Event.source_type == source_type)
    if min_priority is not None:
        stmt = stmt.where(Event.priority_score >= min_priority)
    if since:
        stmt = stmt.where(Event.published_at >= since)
    stmt = stmt.order_by(desc(Event.priority_score) if order == "priority" else desc(Event.published_at))
    events = (await db.execute(stmt)).scalars().all()
    return [event_out(e) for e in events]


@router.get("/{event_id}")
async def get_event(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Event)
        .options(
            selectinload(Event.source),
            selectinload(Event.entities).selectinload(EventEntity.entity),
            selectinload(Event.analyses),
        )
        .where(Event.id == event_id)
    )
    event = (await db.execute(stmt)).scalar_one_or_none()
    if event is None:
        raise HTTPException(404, "event not found")
    return event_out(event, include_body=True)
