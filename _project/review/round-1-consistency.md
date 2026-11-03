# Round 1 — consistency lens (reviewer-consistency, 2026-11-03)

Read-only, nothing executed. All eight briefed checks run; checks 1, 3, 4, 6, 7, 8 fail.

## Findings

| # | Severity | File:line | Problem | Evidence | Fix | Status |
|---|---|---|---|---|---|---|
| 1 | High | backend/app/worker.py:112,147 | `rescore_events` scores with `source_authority=e.source_confidence` (defaults 0.5, never set from trust) and is enqueued on EVERY worker boot despite "One-off maintenance" docstring. Every restart rewrites all priority scores with wrong authority (KEV 1.0 → 0.5, −0.125 swing) and drops corroboration (`corroborated=False`). | ingest.py:114 uses `source.trust_score`; models.py:91 default 0.5 | Pass `e.source.trust_score`, preserve corroboration; stop enqueuing on startup | open |
| 2 | High | README.md:63 | Quickstart `curl -X POST .../fetch` has no x-api-key; with the fail-closed guard and empty default key the documented command returns 403 | main.py:72-81; .env.example ships API_WRITE_KEY= empty; README:127 shows the keyed form | Add the header to the quickstart | open |
| 3 | High | backend/app/connectors/github_releases.py:49,58 | `taxonomy=["ai.inference"]` and `source_type="repository_release"` hardcoded for every release — wrong for the mcp-spec source (source_type "specification"): MCP spec releases are labelled ai.inference → wrong digest section and wrong boost. Contradicts seeds.py:4-5 "registry row is the source of truth". | seeds.py:53-63; classify.py:24 can't match spaceless repo names | Derive taxonomy/source_type from the source registry row | open |
| 4 | High | backend/app/api/digest.py:26,37,62-63 | Models section prefixes omit `ai.safety`/`ai.evaluation` → they fall to "other" → excluded. Jailbreak/red-teaming/benchmark news — the owner's core interest — can NEVER appear in the daily ten. | classify.py:22-23 produces both; llm.py:42-43 allows both | Add them to a section and to INTEREST_BOOST | open |
| 5 | High | backend/app/pipeline/classify.py:13 | `\bexploit\b` fires on the mere word "exploit", ubiquitous in advisory prose; digest gate then trusts the label (digest.py:46-47), score.py:91 compounds (`"poc" in body` matches "epoch", +0.4). Direct mechanism for generic CVEs passing the "public exploit" gate into the digest. | digest.py:41-42 claims the gate requires actual PoC publication | Tighten to publication-shaped signals; don't trust this label alone in has_public_exploit | open |
| 6 | High | backend/app/mcp_server.py:131 | `Event.taxonomy.overlap([...])` — ARRAY comparator on a JSON column; `find_model_releases` MCP tool will fail at call time (static evidence) | models.py:90 JSON column; digest.py:115/dedupe.py:46 cast to JSONB | Cast to JSONB containment | open |
| 7 | Medium | backend/app/api/digest.py:35,24-30,69-70 | Dead inner loop (`prefix` unused); SECTIONS ordering means an event with offsec.* + ai.*/mcp.* labels is claimed by mcp/models first, BYPASSING the exploitation PoC gate (only applied to section=="exploitation") — e.g. a vLLM advisory enters "models" ungated | — | Drop inner loop; gate any event carrying offsec.vulnerability/exploit regardless of section | open |
| 8 | Medium | backend/app/pipeline/score.py:29,44,51 | Boosted labels `ai.model.weights`, `research.benchmark`, `offsec.tradecraft` are only producible via the LLM; with LLM failure they never fire | classify.py has no rule for any of the three | Add classifier rules | open |
| 9 | Medium | frontend/components/FeedbackButtons.tsx:20-25 | Feedback POST sends no key and shows "✓" even on 403; write guard means UI feedback can never be recorded. README claims NEXT_PUBLIC_READ_ONLY=true on public build; compose never sets it | main.py:79-81; README:122-123; compose:102-117 | Check res.ok; decide guard exemption or wire key; set the env where claimed | open |
| 10 | Medium | backend/app/config.py:37-38 | `scheduler_interval` read by nothing; worker.py:157 hardcodes cron | — | Delete or wire | open |
| 11 | Medium | backend/app/main.py:74 | API_WRITE_KEY read via os.environ, the only setting outside pydantic Settings (which loads .env itself) — host-side runs get it empty → writes silently denied | config.py:5 | Move into Settings | open |
| 12 | Medium | README.md:14,135 | MinIO vs SeaweedFS | compose:30-34 | Replace | open |
| 13 | Medium | backend/app/pipeline/ingest.py:153 | LLM taxonomy_labels merged with no whitelist; prompt says "from this set only" but code never enforces | llm.py:39 | Intersect with one canonical label set shared by classify/llm/score/digest | open |
| 14 | Medium | backend/app/api/events.py:38, search/hybrid.py:22 | Three query styles for the same JSON column (`contains` bare, JSONB cast, ARRAY overlap) | digest.py:115, dedupe.py:46, mcp_server.py:131 | Standardise on JSONB containment | open |
| 15 | Medium | backend/app/api/digest.py:126-138 | `sections` + `emerging_themes` computed, snapshotted, typed in lib/api.ts, rendered by NOTHING | page.tsx renders only top_events + counters | Render them or stop computing | open |
| 16 | Low | classify.py:19 | Label ai.model.quantisation (UK) but pattern `quantiz` matches only US spellings | — | `quanti[sz]` | open |
| 17 | Low | digest.py:59 | Comment mentions Reddit; no Reddit source exists | seeds.py | Drop "Reddit" | open |
| 18 | Low | digest.py:112 | "requires action" bar 0.7 vs alert_threshold 0.75 — two bars for one concept | config.py:29 | One constant or rename | open |
| 19 | Low | frontend (page.tsx:32, EventCard.tsx:51, search:53, sources:32, events/[id]:28-29) | toLocale*String() with no locale → en-US dates for a UK owner | CLAUDE.md §1 | Pass "en-GB" | open |
| 20 | Low | README.md:88-89 | Layout omits pipeline/alerts.py and connectors/seeds.py | — | Add | open |
| 21 | Low | frontend/app/archive/page.tsx:26 | "first snapshot generated on the next daily run" — actually generated on first dashboard visit | digest.py:155-157 | Correct wording | open |

## Briefed checks
1 FAIL (3,4,5,8,13) · 2 PASS w/ Low (17) · 3 FAIL (3) · 4 FAIL (2,12,20; routes/env otherwise match) · 5 PASS w/ Medium (9,15) · 6 FAIL (7; per-section cap itself behaves as documented) · 7 FAIL (1; cron claims match README) · 8 FAIL Low (16,19; prose otherwise UK).

## Not checked
Nothing executed (findings 2, 6, 14 are static conclusions). globals.css, Dockerfiles, db.py internals, package manifests not reviewed. Whether live feed bodies trigger the claimed classifier rules not verified.

Verdict: not clean — 6 High, 9 Medium. Root-cause cluster for the owner's symptom: findings 3, 4, 5, 7.
