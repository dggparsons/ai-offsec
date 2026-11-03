"""Hybrid retrieval: PostgreSQL full-text (lexical) + pgvector (semantic),
fused with reciprocal-rank fusion. Structured filters apply before fusion.

At MVP scale this runs entirely inside Postgres. The query interface is the
seam: swapping in OpenSearch/Qdrant later only reimplements this module.
"""

from typing import Any

from sqlalchemy import Select, cast, func, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event
from app.pipeline.embed import embed_text
from app.pipeline.llm import strip_markup

RRF_K = 60  # standard RRF constant


def _apply_filters(stmt: Select, filters: dict[str, Any]) -> Select:
    if v := filters.get("taxonomy"):
        stmt = stmt.where(cast(Event.taxonomy, JSONB).contains([v]))
    if v := filters.get("source_type"):
        stmt = stmt.where(Event.source_type == v)
    if v := filters.get("source_id"):
        stmt = stmt.where(Event.source_id == v)
    if v := filters.get("since"):
        stmt = stmt.where(Event.published_at >= v)
    if v := filters.get("min_priority"):
        stmt = stmt.where(Event.priority_score >= v)
    if v := filters.get("cve"):
        stmt = stmt.where(cast(Event.identifiers["cve"], JSONB).contains([v.upper()]))
    return stmt


async def hybrid_search(
    db: AsyncSession, query: str, filters: dict[str, Any] | None = None, limit: int = 25
) -> list[dict[str, Any]]:
    filters = filters or {}
    candidates = max(limit * 4, 50)

    # --- Lexical leg ---
    tsq = func.plainto_tsquery("english", query)
    lex_rank = func.ts_rank_cd(Event.search_vector, tsq).label("lex_rank")
    lex_stmt = _apply_filters(
        select(Event.id, lex_rank).where(Event.search_vector.op("@@")(tsq)), filters
    ).order_by(lex_rank.desc()).limit(candidates)

    # --- Semantic leg ---
    query_vec, _ = await embed_text(query)
    sem_dist = Event.embedding.cosine_distance(query_vec).label("sem_dist")
    sem_stmt = _apply_filters(
        select(Event.id, sem_dist).where(Event.embedding.is_not(None)), filters
    ).order_by(sem_dist).limit(candidates)

    lex_rows = (await db.execute(lex_stmt)).all()
    sem_rows = (await db.execute(sem_stmt)).all()

    # --- Reciprocal-rank fusion + priority tie-break ---
    # Text relevance dominates, but fresh AI-relevant high-priority items
    # outrank stale bulk CVEs on equal relevance (round-2: a 2021 Oracle CVE
    # was the #2 hit for "jailbreak"). The semantic leg only sees rows with
    # real embeddings — pseudo-hash fallbacks are stored as NULL, never
    # ranked (round-2: hash junk ordered the vector leg randomly).
    scores: dict[Any, float] = {}
    for rank, (eid, _r) in enumerate(lex_rows):
        scores[eid] = scores.get(eid, 0.0) + 1.0 / (RRF_K + rank + 1)
    for rank, (eid, _d) in enumerate(sem_rows):
        scores[eid] = scores.get(eid, 0.0) + 1.0 / (RRF_K + rank + 1)

    if not scores:
        return []

    candidate_ids = [
        eid for eid, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[: max(limit * 2, 50)]
    ]
    events = (await db.execute(select(Event).where(Event.id.in_(candidate_ids)))).scalars().all()
    by_id = {e.id: e for e in events}
    final = {
        eid: scores[eid] * 10 + 0.2 * (by_id[eid].priority_score if eid in by_id else 0.0)
        for eid in candidate_ids
    }
    top_ids = [eid for eid, _ in sorted(final.items(), key=lambda kv: kv[1], reverse=True)[:limit] if eid in by_id]
    return [
        {
            "id": str(eid),
            "title": by_id[eid].title,
            "source_url": by_id[eid].source_url,
            "source_type": by_id[eid].source_type,
            "published_at": by_id[eid].published_at.isoformat() if by_id[eid].published_at else None,
            "taxonomy": by_id[eid].taxonomy,
            "priority_score": by_id[eid].priority_score,
            "rrf_score": round(scores[eid], 6),
            # Plain-prose snippet: body text carries markdown/HTML remnants
            # from advisories and release notes (round-1 fix). Title-only
            # records fall back to the TLDR rather than a blank snippet.
            "snippet": strip_markup(by_id[eid].body_text or "")[:400] or (by_id[eid].tldr or ""),
        }
        for eid in top_ids
    ]


SEARCH_VECTOR_SQL = text(
    "UPDATE events SET search_vector = "
    "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body_text, '')) "
    "WHERE id = :event_id"
)
