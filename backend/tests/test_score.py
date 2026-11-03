"""Scoring: PoC substring accidents and the AI-relevance mission gate
(round-1 findings: 'epoch' matched 'poc'; generic CVEs outscored AI news)."""

from datetime import datetime, timezone

from app.pipeline.score import _mentions_poc, score_event


def test_poc_word_boundary():
    assert not _mentions_poc("An epoch-making change to the pocket scheduler.")
    assert _mentions_poc("PoC available on GitHub.")
    assert _mentions_poc("proof-of-concept published")


def _score(ai_relevant: bool) -> float:
    now = datetime.now(timezone.utc)
    score, _ = score_event(
        source_authority=0.9,
        taxonomy=["offsec.vulnerability"],
        identifiers={"cve": ["CVE-2026-0001"]},
        body="A vulnerability.",
        published_at=now,
        is_novel=True,
        corroborated=False,
        source_type="security_advisory",
        ai_relevant=ai_relevant,
    )
    return score


def test_non_ai_penalty_outweighs_cve_drama():
    assert _score(True) - _score(False) >= 0.3
