"""Daily digest: build once, snapshot, serve.

The daily cron job (worker.py) calls build_digest() and stores an immutable
snapshot per UTC day — "log the old stuff". The API serves the latest
snapshot (recomputed live only if today's is missing), plus a history index.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import cast

from app.api.serializers import event_out
from app.db import get_db
from app.models import Digest, Event, EventEntity

router = APIRouter(prefix="/api/digest", tags=["digest"])

# Section definitions: (key, title, taxonomy prefixes that qualify)
SECTIONS = [
    ("mcp", "MCP & agent plumbing", ("mcp.",)),
    ("models", "Models & inference", ("ai.model.", "ai.inference", "ai.agent")),
    ("research", "Research & papers", ("research.",)),
    ("exploitation", "Exploitation", ("offsec.",)),
    ("enterprise", "Enterprise adoption", ("enterprise.", "vendor.")),
]


def section_of(taxonomy: list[str]) -> str:
    for key, _title, prefixes in SECTIONS:
        if any(t.startswith(prefixes) for t in taxonomy for prefix in prefixes):
            return key
    return "other"


def has_public_exploit(event: Event) -> bool:
    """'Key CVEs only if they're public': KEV membership or an actual
    PoC/exploit publication — not merely an RCE-shaped description."""
    if event.source_type == "exploited_vulnerability":
        return True
    taxonomy = event.taxonomy or []
    if "offsec.exploit" in taxonomy:
        return True
    body = (event.body_text or "").lower()
    return "proof-of-concept" in body or "poc exploit" in body or "exploit is public" in body


def digest_worthy(event: Event, section: str) -> bool:
    """Editorial gate for the daily read. Everything remains searchable —
    this only decides what earns a place on the front page.

    - NVD bulk records never make the digest (a CVE that matters gets
      corroborated by KEV / a PoC source anyway).
    - Exploitation requires public exploitation signal (KEV or PoC).
    - Low-trust discovery sources (HN, Reddit) never occupy curated sections.
    - 'other' (uncategorised) items don't make the daily read.
    """
    if section == "other":
        return False
    if event.source_type == "vulnerability_record":
        return False
    trust = event.source.trust_score if event.source else 0.5
    if trust < 0.5:
        return False
    if section == "exploitation":
        return has_public_exploit(event)
    return True


async def build_digest(db: AsyncSession, hours: int = 24) -> dict:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    # Window on the source's own publication time (falling back to ingest
    # time), so back-catalogue ingestion doesn't masquerade as fresh news.
    in_window = func.coalesce(Event.published_at, Event.created_at) >= since
    base = select(Event).where(in_window)

    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0

    top_all = (
        await db.execute(
            base.options(
                selectinload(Event.source),
                selectinload(Event.entities).selectinload(EventEntity.entity),
                selectinload(Event.analyses),
            )
            .order_by(desc(Event.priority_score))
            .limit(200)
        )
    ).scalars().all()

    # Apply the editorial gate, then pick the day's ten best with a
    # per-section cap so one firehose topic can't crowd out the rest.
    gated = [(e, section_of(e.taxonomy)) for e in top_all]
    worthy = [(e, s) for e, s in gated if digest_worthy(e, s)]

    top: list[Event] = []
    per_section: dict[str, int] = {}
    for e, s in worthy:
        if e.priority_score < 0.45:  # quality floor: fewer beats filler
            continue
        if per_section.get(s, 0) >= 3:
            continue
        top.append(e)
        per_section[s] = per_section.get(s, 0) + 1
        if len(top) >= 10:
            break

    actionable = [e for e in top if e.priority_score >= 0.7]

    # Emerging themes: taxonomy frequency over the window.
    label = func.jsonb_array_elements_text(cast(Event.taxonomy, JSONB)).label("label")
    taxonomy_rows = (
        await db.execute(
            select(label, func.count().label("n"))
            .where(in_window)
            .group_by(label)
            .order_by(desc("n"))
            .limit(10)
        )
    ).all()

    sections: dict[str, list] = {key: [] for key, _t, _p in SECTIONS}
    for e in top:
        sections[section_of(e.taxonomy)].append(event_out(e))

    return {
        "window_hours": hours,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items_requiring_action": len(actionable),
        "material_developments": len([e for e in top if e.priority_score < 0.7]),
        "suppressed_low_priority": max(total - len(top), 0),
        "top_events": [event_out(e) for e in top],
        "sections": sections,
        "emerging_themes": [{"label": r.label, "count": r.n} for r in taxonomy_rows],
    }


async def snapshot_today(db: AsyncSession) -> dict:
    """Build and store today's snapshot (replacing any earlier one today)."""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    content = await build_digest(db)
    await db.execute(delete(Digest).where(Digest.day == day))
    db.add(Digest(day=day, content=content))
    await db.commit()
    return content


@router.get("/daily")
async def daily_digest(db: AsyncSession = Depends(get_db)):
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = (await db.execute(select(Digest).where(Digest.day == day))).scalar_one_or_none()
    if row is None:
        return await snapshot_today(db)
    return row.content


@router.get("/history")
async def digest_history(db: AsyncSession = Depends(get_db), limit: int = Query(30, le=90)):
    rows = (
        await db.execute(select(Digest.day, Digest.created_at).order_by(desc(Digest.day)).limit(limit))
    ).all()
    return [{"day": r.day, "generated_at": r.created_at.isoformat()} for r in rows]


@router.get("/day/{day}")
async def digest_for_day(day: str, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(Digest).where(Digest.day == day))).scalar_one_or_none()
    if row is None:
        return {"day": day, "content": None}
    return {"day": day, "content": row.content}
