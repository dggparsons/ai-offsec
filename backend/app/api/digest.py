"""Daily digest: the executive view. Emphasises material changes only —
a small number of high-priority items, emerging taxonomy activity, and the
count of suppressed lower-priority updates."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import cast, desc, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.serializers import event_out
from app.db import get_db
from app.models import Event, EventEntity

router = APIRouter(prefix="/api/digest", tags=["digest"])


@router.get("/daily")
async def daily_digest(db: AsyncSession = Depends(get_db), hours: int = Query(24, le=168)):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    base = select(Event).where(Event.created_at >= since)

    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0

    top = (
        await db.execute(
            base.options(
                selectinload(Event.source),
                selectinload(Event.entities).selectinload(EventEntity.entity),
                selectinload(Event.analyses),
            )
            .order_by(desc(Event.priority_score))
            .limit(10)
        )
    ).scalars().all()

    actionable = [e for e in top if e.priority_score >= 0.7]

    # Emerging themes: taxonomy frequency over the window.
    label = func.jsonb_array_elements_text(cast(Event.taxonomy, JSONB)).label("label")
    taxonomy_rows = (
        await db.execute(
            select(label, func.count().label("n"))
            .where(Event.created_at >= since)
            .group_by(label)
            .order_by(desc("n"))
            .limit(10)
        )
    ).all()

    return {
        "window_hours": hours,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items_requiring_action": len(actionable),
        "material_developments": len(top) - len(actionable),
        "suppressed_low_priority": max(total - len(top), 0),
        "top_events": [event_out(e) for e in top],
        "emerging_themes": [{"label": r.label, "count": r.n} for r in taxonomy_rows],
    }
