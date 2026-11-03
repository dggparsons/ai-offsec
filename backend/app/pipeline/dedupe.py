"""Deduplication and change detection, layered per the design doc:

1. Exact SHA-256 of raw bytes          -> identical re-fetch, skip work
2. Normalised hash                     -> formatting-only change, skip re-analysis
3. Identifier match (CVE/GHSA/arXiv..) -> same object from another source:
   corroboration, not duplication       -> merge signal, boost score
4. (Extension point) SimHash/MinHash + embedding similarity for syndicated
   copies — wire in when volume justifies it.
"""

import hashlib

from sqlalchemy import cast, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event
from app.pipeline.normalize import normalized_hash_input


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_hash(title: str, body: str) -> str:
    return hashlib.sha256(normalized_hash_input(title, body).encode()).hexdigest()


async def find_existing_event(
    db: AsyncSession, source_db_id, external_id: str | None, identifiers: dict
) -> Event | None:
    """Locate the canonical event for this item, preferring stable IDs."""
    if external_id:
        q = await db.execute(
            select(Event).where(Event.source_id == source_db_id, Event.external_id == external_id)
        )
        if event := q.scalar_one_or_none():
            return event
    # Cross-source corroboration: same CVE/GHSA already tracked elsewhere.
    for key in ("cve", "ghsa", "arxiv"):
        values = identifiers.get(key) or []
        if not values:
            continue
        q = await db.execute(
            select(Event)
            .where(cast(Event.identifiers[key], JSONB).contains(values))
            .limit(1)
        )
        if event := q.scalar_one_or_none():
            return event
    return None
