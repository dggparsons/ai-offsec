from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.search.hybrid import hybrid_search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
async def search(
    db: AsyncSession = Depends(get_db),
    q: str = Query(..., min_length=1),
    limit: int = Query(25, le=100),
    taxonomy: str | None = None,
    source_type: str | None = None,
    since: datetime | None = None,
    min_priority: float | None = None,
    cve: str | None = None,
):
    filters = {
        k: v
        for k, v in {
            "taxonomy": taxonomy,
            "source_type": source_type,
            "since": since,
            "min_priority": min_priority,
            "cve": cve,
        }.items()
        if v is not None
    }
    return await hybrid_search(db, q, filters=filters, limit=limit)
