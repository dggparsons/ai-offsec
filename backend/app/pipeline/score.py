"""Relevance scoring.

First-generation weighted heuristic (weights from the design doc), tuned by
editorial interest: bulk vulnerability records are suppressed unless they
carry exploitation signal (KEV membership, public PoC), while model releases,
research, MCP changes and AI-assisted tradecraft get boosted. The
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

# Editorial interest: what a reader of this platform actually wants to see.
INTEREST_BOOST = {
    "ai.model.release": 0.18,
    "ai.model.weights": 0.14,
    "ai.model.architecture": 0.08,
    "ai.model.quantisation": 0.08,
    "ai.inference": 0.10,
    "ai.agent": 0.10,
    "ai.safety": 0.14,
    "ai.evaluation": 0.08,
    "research.paper": 0.12,
    "research.benchmark": 0.08,
    "research.code": 0.06,
    "mcp.specification": 0.12,
    "mcp.server": 0.08,
    "mcp.security": 0.14,
    "offsec.ai-assisted": 0.14,
    "offsec.exploit": 0.10,
    "offsec.exploit-technique": 0.08,
    "enterprise.deployment": 0.08,
    "enterprise.case-study": 0.06,
}

# Bulk CVE feeds (NVD etc.) are background noise unless exploited/PoC'd.
BULK_SOURCE_TYPES = {"vulnerability_record"}
BULK_PENALTY = 0.30

# Mission gate (review round 1): events with no AI/LLM connection must never
# outrank AI news, whatever their CVSS drama. The digest also hard-gates on
# ai_relevant; this keeps alerts and orderings consistent with that.
AI_RELEVANCE_BOOST = 0.10
NON_AI_PENALTY = 0.25

_POC_RE = None


def _mentions_poc(body: str) -> bool:
    """Word-bounded: 'epoch'/'pocket' must not count as PoC (round-1 fix)."""
    global _POC_RE
    if _POC_RE is None:
        import re

        _POC_RE = re.compile(r"\bpoc\b|proof[- ]of[- ]concept", re.I)
    return bool(_POC_RE.search(body))


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


def exploitability_score(identifiers: dict, taxonomy: list[str], body: str, source_type: str = "") -> float:
    # KEV membership IS the exploitation signal.
    if source_type == "exploited_vulnerability":
        return 1.0
    score = 0.0
    labels = set(taxonomy)
    if "offsec.exploit" in labels or _mentions_poc(body):
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
    source_type: str = "",
    internal_asset_hits: int = 0,
    ai_relevant: bool = True,
) -> tuple[float, dict]:
    labels = set(taxonomy)
    is_bulk = source_type in BULK_SOURCE_TYPES
    exploitability = exploitability_score(identifiers, taxonomy, body, source_type)
    components = {
        "source_authority": source_authority,
        # Bulk CVE records are only interesting with real exploitation signal.
        "offensive_relevance": (
            (1.0 if exploitability >= 0.6 else 0.15)
            if is_bulk
            else (1.0 if labels & OFFENSIVE_LABELS else 0.15)
        ),
        "enterprise_relevance": 1.0 if labels & ENTERPRISE_LABELS else 0.1,
        "novelty": 1.0 if is_novel else 0.2,
        "exploitability": exploitability,
        "internal_asset_relevance": min(internal_asset_hits * 0.5, 1.0),
        "corroboration": 1.0 if corroborated else 0.0,
        "recency": recency_score(published_at),
    }
    total = sum(WEIGHTS[k] * v for k, v in components.items())

    boost = sum(INTEREST_BOOST.get(t, 0.0) for t in labels)
    if is_bulk and exploitability < 0.6:
        boost -= BULK_PENALTY
    boost += AI_RELEVANCE_BOOST if ai_relevant else -NON_AI_PENALTY
    components["ai_relevant"] = 1.0 if ai_relevant else 0.0
    components["interest_boost"] = round(boost, 4)
    total = max(0.0, min(1.0, total + boost))
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
