"""Digest editorial gate: the daily read is AI/LLM news only (round-1
end-user finding #1 — 4 of 7 front-page items were generic CVEs)."""

from types import SimpleNamespace

from app.api.digest import QUALITY_FLOOR, digest_worthy, eligible, section_of, select_top


def _event(ai_relevant=True, source_type="security_advisory", trust=0.9, score=0.9, taxonomy=(), eid=None, body="x" * 250):
    return SimpleNamespace(
        id=eid or object(),
        ai_relevant=ai_relevant,
        source_type=source_type,
        source=SimpleNamespace(trust_score=trust),
        priority_score=score,
        taxonomy=list(taxonomy),
        body_text=body,
    )


def test_non_ai_event_never_makes_digest():
    assert not digest_worthy(_event(ai_relevant=False))


def test_ai_relevant_advisory_makes_digest():
    assert digest_worthy(_event())


def test_nvd_bulk_records_never_makes_digest():
    assert not digest_worthy(_event(source_type="vulnerability_record"))


def test_low_trust_discovery_never_makes_digest():
    assert not digest_worthy(_event(source_type="forum_discovery", trust=0.3))


def test_safety_and_evals_have_a_section():
    assert section_of(["ai.safety"]) == "safety"
    assert section_of(["ai.evaluation"]) == "safety"
    assert section_of(["offsec.vulnerability"]) == "exploitation"
    assert section_of([]) == "other"


def test_quality_floor_excludes_below_but_not_at():
    below = _event(score=QUALITY_FLOOR - 0.01)
    at = _event(score=QUALITY_FLOOR)
    assert eligible([below, at]) == [at]


def test_per_section_cap_then_backfill():
    # 4 events in each of 3 sections, cap 3: capped pass takes 9,
    # backfill tops the list up to 10 from the remaining eligible pool.
    events = []
    for tax in (["offsec.vulnerability"], ["ai.inference"], ["research.paper"]):
        events.extend(_event(taxonomy=tax, eid=object()) for _ in range(4))
    top = select_top(events)
    assert len(top) == 10
    # 20 identical-section events: cap 3, then backfill ignores the cap —
    # fewer-beats-filler never means publishing a short list when the pool
    # has eligible items.
    same = [_event(taxonomy=["ai.inference"], eid=object()) for _ in range(20)]
    assert len(select_top(same)) == 10


def test_short_pool_publishes_short_list():
    events = [_event(eid=object()) for _ in range(3)]
    assert len(select_top(events)) == 3


def test_narrative_stub_excluded_but_structured_advisory_allowed():
    stub = _event(source_type="vendor_blog", body="Sponsors only — subscribe!")
    assert not digest_worthy(stub)
    short_advisory = _event(source_type="security_advisory", body="RCE in foo.")
    assert digest_worthy(short_advisory)


def test_cap_never_suppresses_a_better_story():
    # Round-2: a 0.90 models release must displace a 0.50 item from a
    # quieter section — the cap guards diversity, not mediocrity.
    models = [_event(taxonomy=["ai.inference"], score=s, eid=object()) for s in (0.99, 0.98, 0.97, 0.90)]
    filler = (
        [_event(taxonomy=["ai.safety"], score=0.5, eid=object())]
        + [_event(taxonomy=["research.paper"], score=0.5, eid=object()) for _ in range(2)]
        + [_event(taxonomy=["offsec.vulnerability"], score=0.5, eid=object()) for _ in range(4)]
    )
    worthy = sorted(models + filler, key=lambda e: e.priority_score, reverse=True)
    top = select_top(worthy)
    assert len(top) == 10
    scores = [e.priority_score for e in top]
    assert 0.90 in scores  # the overflow release made it in
    assert scores == sorted(scores, reverse=True)  # output stays score-ordered
