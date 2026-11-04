"""Daily digest: build once, snapshot, serve.

The daily cron job (worker.py) calls build_digest() and stores an immutable
snapshot per UTC day — "log the old stuff". The API serves the latest
snapshot (recomputed live only if today's is missing), plus a history index.

Editorial contract (review round 1, 2026-11-03): the daily read is AI/LLM
news ONLY. Generic CVEs with no AI connection stay searchable but never
occupy the front page, however high their CVSS. Counters must be truthful:
"suppressed" means below the quality floor or outside the mission, and
anything eligible that didn't fit is reported as such, never hidden.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.serializers import event_out
from app.config import settings
from app.db import get_db
from app.models import Digest, Entity, Event, EventEntity

router = APIRouter(prefix="/api/digest", tags=["digest"])

# Section definitions: (key, title, taxonomy prefixes that qualify).
# Order is classification precedence (first match wins); display order is
# the frontend's business. Titles are reader-facing, in the owner's language.
SECTIONS = [
    ("mcp", "MCP & agent plumbing", ("mcp.",)),
    ("safety", "Jailbreaks, red-teaming & evals", ("ai.safety", "ai.evaluation")),
    ("models", "Models & local LLMs", ("ai.model.", "ai.inference", "ai.agent")),
    ("research", "Research & papers", ("research.",)),
    ("exploitation", "CVEs & exploits in AI software", ("offsec.",)),
    ("enterprise", "Enterprise adoption", ("enterprise.", "vendor.")),
]

QUALITY_FLOOR = 0.45  # fewer beats filler
PER_SECTION_CAP = 3
TOP_N = 10
# Narrative sources (blogs, papers, forums) must have something to read: a
# paywalled stub or one-line announcement is not morning-reading material.
MIN_BODY_CHARS = 200
NARRATIVE_SOURCE_TYPES = {"security_research", "vendor_blog", "forum_discovery", "research", "mailing_list"}


def section_of(taxonomy: list[str]) -> str:
    for key, _title, prefixes in SECTIONS:
        if any(t.startswith(prefixes) for t in taxonomy):
            return key
    return "other"


def digest_worthy(event: Event) -> bool:
    """Editorial gate for the daily read. Everything remains searchable —
    this only decides what earns a place on the front page.

    - Mission gate: only AI/LLM-relevant events (event.ai_relevant).
    - NVD bulk records never make the digest (a CVE that matters gets
      corroborated by KEV / an advisory source anyway).
    - Low-trust discovery sources (HN) never occupy the daily read.
    - Narrative items must carry substance (a paywalled stub is not news).
    """
    if not event.ai_relevant:
        return False
    if event.source_type == "vulnerability_record":
        return False
    if event.source_type in NARRATIVE_SOURCE_TYPES and len(event.body_text or "") < MIN_BODY_CHARS:
        return False
    trust = event.source.trust_score if event.source else 0.5
    return trust >= 0.5


def eligible(events) -> list:
    """Events allowed onto the front page: editorial gate + quality floor."""
    return [e for e in events if digest_worthy(e) and e.priority_score >= QUALITY_FLOOR]


def select_top(worthy: list, top_n: int = TOP_N, per_section_cap: int = PER_SECTION_CAP) -> list:
    """Pick the day's best. The per-section cap is a diversity guard, never a
    ceiling that suppresses a better story: after the capped pass, any
    excluded item that outscores the weakest included one takes its place
    (round-2: vLLM at 0.90 lost its slot to a 0.71 CVE under a hard cap).
    If sections starve, remaining slots fill from the eligible pool rather
    than publishing a short list."""
    top: list = []
    overflow: list = []
    per_section: dict[str, int] = {}
    for e in worthy:  # already ordered by score, best first
        s = section_of(e.taxonomy)
        if per_section.get(s, 0) >= per_section_cap:
            overflow.append(e)
            continue
        top.append(e)
        per_section[s] = per_section.get(s, 0) + 1
        if len(top) >= top_n:
            overflow.extend(worthy[worthy.index(e) + 1 :])
            break
    for e in overflow:
        if len(top) < top_n:
            top.append(e)
            continue
        weakest = min(top, key=lambda x: x.priority_score)
        if e.priority_score > weakest.priority_score:
            top.remove(weakest)
            top.append(e)
    top.sort(key=lambda x: x.priority_score, reverse=True)
    return top[:top_n]


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
            .limit(300)
        )
    ).scalars().all()

    worthy = eligible(top_all)
    top = select_top(worthy)
    eligible_not_shown = max(len(worthy) - len(top), 0)
    actionable = [e for e in top if e.priority_score >= settings.alert_threshold]

    # Emerging themes: most-referenced entities (models, repos, CVEs) in the
    # window — not raw taxonomy counts, which just restate the feed mix.
    theme_rows = (
        await db.execute(
            select(Entity.type, Entity.name, func.count().label("n"))
            .join(EventEntity, EventEntity.entity_id == Entity.id)
            .join(Event, Event.id == EventEntity.event_id)
            .where(in_window, Event.ai_relevant)
            .group_by(Entity.type, Entity.name)
            .order_by(desc("n"))
            .limit(10)
        )
    ).all()

    sections: dict[str, list] = {key: [] for key, _t, _p in SECTIONS}
    for e in top:
        sections.setdefault(section_of(e.taxonomy), []).append(event_out(e))

    return {
        "window_hours": hours,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items_requiring_action": len(actionable),
        "material_developments": len(top) - len(actionable),
        "eligible_not_shown": eligible_not_shown,
        "suppressed_low_priority": max(total - len(top) - eligible_not_shown, 0),
        "top_events": [event_out(e) for e in top],
        "sections": sections,
        "emerging_themes": [
            {"label": f"{r.type}:{r.name}", "count": r.n} for r in theme_rows
        ],
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
