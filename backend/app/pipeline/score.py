"""Relevance scoring.

First-generation weighted heuristic (weights from the design doc). The
`learn_from_feedback` extension point will refit these weights from analyst
actions (open/save/escalate/dismiss) once enough feedback accumulates.
"""

from datetime import datetime, timezone

WEIGHTS = {
    "source_authority": 0.25,
    "offensive_relevance": 0.20,
    "enterprise_relevance": 0.15,
    "novelty": 0.15,
    "exploitability": 0.10,
    "internal_asset_relevance": 0.05,
    "corroboration": 0.05,
    "recency": 0.05,
}

OFFENSIVE_LABELS = {
    "offsec.vulnerability",
    "offsec.exploit",
    "offsec.exploit-technique",
    "offsec.tool",
    "offsec.tradecraft",
    "offsec.ai-assisted",
    "mcp.security",
}
ENTERPRISE_LABELS = {
    "enterprise.deployment",
    "enterprise.case-study",
    "enterprise.procurement",
    "enterprise.integration",
    "enterprise.governance",
}


def recency_score(published_at: datetime | None, now: datetime | None = None) -> float:
    if published_at is None:
        return 0.3
    now = now or datetime.now(timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    age_hours = max((now - published_at).total_seconds() / 3600, 0)
    if age_hours <= 6:
        return 1.0
    if age_hours <= 24:
        return 0.8
    if age_hours <= 72:
        return 0.5
    if age_hours <= 168:
        return 0.3
    return 0.1


def exploitability_score(identifiers: dict, taxonomy: list[str], body: str) -> float:
    score = 0.0
    labels = set(taxonomy)
    if "offsec.exploit" in labels or "proof-of-concept" in body.lower() or "poc" in body.lower():
        score += 0.4
    if identifiers.get("cve"):
        score += 0.2
    if "offsec.vulnerability" in labels:
        score += 0.2
    lowered = body.lower()
    if "remote code execution" in lowered or "pre-auth" in lowered or "unauthenticated" in lowered:
        score += 0.2
    return min(score, 1.0)


def score_event(
    *,
    source_authority: float,
    taxonomy: list[str],
    identifiers: dict,
    body: str,
    published_at: datetime | None,
    is_novel: bool,
    corroborated: bool,
    internal_asset_hits: int = 0,
) -> tuple[float, dict]:
    labels = set(taxonomy)
    components = {
        "source_authority": source_authority,
        "offensive_relevance": 1.0 if labels & OFFENSIVE_LABELS else 0.15,
        "enterprise_relevance": 1.0 if labels & ENTERPRISE_LABELS else 0.1,
        "novelty": 1.0 if is_novel else 0.2,
        "exploitability": exploitability_score(identifiers, taxonomy, body),
        "internal_asset_relevance": min(internal_asset_hits * 0.5, 1.0),
        "corroboration": 1.0 if corroborated else 0.0,
        "recency": recency_score(published_at),
    }
    total = sum(WEIGHTS[k] * v for k, v in components.items())
    return round(total, 4), components


def severity_for(score: float, taxonomy: list[str]) -> str:
    labels = set(taxonomy)
    if score >= 0.85 or (score >= 0.7 and labels & {"offsec.exploit"}):
        return "critical"
    if score >= 0.7:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"
