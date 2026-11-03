from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.serializers import alert_out
from app.db import get_db
from app.models import Alert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    severity: str | None = None,
    limit: int = Query(50, le=200),
):
    stmt = select(Alert).order_by(desc(Alert.created_at)).limit(limit)
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    alerts = (await db.execute(stmt)).scalars().all()
    return [alert_out(a) for a in alerts]
