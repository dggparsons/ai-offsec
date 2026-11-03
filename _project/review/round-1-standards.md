# Round 1 — standards lens (reviewer-standards, 2026-11-03)

Reviewed read-only against ~/.claude/CLAUDE.md and the Claude engineering standards.
Caller note: reviewer had no Bash; `git ls-files` check was NOT run (see Not checked).

## Findings

| # | Severity | File:line | Problem | Evidence | Fix | Status |
|---|---|---|---|---|---|---|
| 1 | High | backend/app/worker.py:51-62 | After the envelope loop, `source.last_success_at` is set and `consecutive_failures` reset unconditionally, even if every envelope failed in the `except Exception: continue` block. A source whose every item fails reports "last success: just now, 0 failures". | CLAUDE.md §3 fail loudly; §2.7 report real results | Count per-envelope failures; only mark success when fetch AND processing succeeded; surface partial status. | open |
| 2 | High | backend/app/connectors/github_releases.py:36-38 | `except Exception: continue  # logged upstream by retry layer` — nothing logs it; tenacity re-raises unlogged. All-repos failure returns `([], {})`, worker records success, back-off never engages. Comment is false. | CLAUDE.md §3 fail loudly; comment asserts logging that does not exist | Log per-repo failure; surface failure count in FetchResult; correct comment. | open |
| 3 | Medium | backend/app/connectors/rss.py:22-25 + api/serializers.py:47-61 | `feedparser.parse` never checks `feed.bozo` or empty entries; a broken feed yields 0 envelopes and the source still shows healthy. Matches the live arxiv-cscr case: zero events ever, fails=0. | CLAUDE.md §2.7 never claim a check passed without running it | Log/count bozo; expose events_total / last_event_at in source health. | open |
| 4 | Medium | backend/app/pipeline/ingest.py:166 + README.md:39-40 | `evidence_event_ids=[str(event.id)]` is circular (the analysis's own event). README sells it as provenance. | CLAUDE.md §3 provenance | Populate with genuinely distinct evidence (raw_object_uri of version analysed, corroborating ids) or soften the claim. | open |
| 5 | Medium | backend/app/pipeline/llm.py:134-139 + ingest.py:153-170 | LLM JSON not schema-validated: confidence gap filled with "medium", taxonomy_labels merged unfiltered against no whitelist, arbitrary keys become public Analysis rows. Untrusted web content feeds the model; unvalidated output lands in the public dataset. | CLAUDE.md §5 schema-check every output | Pydantic-validate; whitelist kinds to ANALYSIS_KINDS and labels to the prompt enum; don't default confidence upward. | open |
| 6 | Medium | backend/app/pipeline/ingest.py:205-209 + README.md:73-77 | `_endpoint_is_local()` is a substring check — any URL containing "ollama"/"127.0.0.1" anywhere counts as local, defeating `allow_external_llm=false`. | README advertises this as a trust boundary | Parse with urlsplit and compare hostname exactly. | open |
| 7 | Medium | repo-wide | Zero tests: none for score.py, digest gate (0.45 floor, per-section cap), dedupe, write guard — on a public deployment. | CLAUDE.md §8 prove each check can fail | Add pytest for score_event, digest_worthy, floor/cap, write-guard middleware. | open |
| 8 | Medium | README.md:14,135 vs docker-compose.yml:30-35 | README says raw store is "MinIO/S3"; compose runs SeaweedFS (and README's own quickstart says SeaweedFS). | inconsistent between files | Replace "MinIO" with "SeaweedFS (S3 API)". | open |
| 9 | Medium | backend/app/config.py:37-38 vs worker.py:157 | `scheduler_interval` setting is dead — sweep cadence is hard-coded `cron(second={0})`. Tuning it changes nothing. | dead flag with false comment | Wire it in or delete it. | open |
| 10 | Low | README.md:142 | "graph UI TBD" in reader-facing README; graph UI missing from the logged stub list. | §2.3 no TBC/TBD visible | Reword and add to stub list. | open |
| 11 | Low | docker-compose.yml:8, config.py:11-12 | `POSTGRES_PASSWORD: intel`, default `minio`/`minio12345` creds in tracked files (local-only mitigations noted). | §3 secrets out of shared files | Parameterise via .env; drop stale minio defaults. | open |
| 12 | Low | backend/app/pipeline/llm.py:108,142 | LLM-failure fallback calls `heuristic_analysis(..., [])` with empty taxonomy, losing the offsec/enterprise significance flags the direct heuristic path produces. | inconsistent between entry points | Pass taxonomy through llm_analysis. | open |
| 13 | Low | backend/app/api/digest.py:33-37 | `for prefix in prefixes` inner loop is dead; `startswith(prefixes)` already takes the tuple. | cosmetic | Delete the inner loop. | open |

## Done-when results
1. No reader-visible placeholders — FAIL (Low, #10). 2. Fail loudly — FAIL (#1-#3). 3. Secrets — PASS with caveat (git ls-files not run; .gitignore lists .env; real API_WRITE_KEY lives in untracked .env — compliant). 4. Provenance — FAIL (#4); prompt_version/model honestly recorded — that part passes. 5. No invented identifiers — PASS with flags (#8, #9); fail-closed write guard verified at main.py:79-81. 6. UK English — PASS. 7. Tests — FAIL (#7).

## Not checked (reviewer had no Bash/network)
- `git ls-files` / git history secrets scan (gitleaks / `git log -p -- .env`) — caller to run; API_WRITE_KEY is live on a public domain.
- Cloudflare WAF/rate-limit claims (README hardening 1-2) — unverifiable from repo.
- `except Exception` sweep across remaining backend files — cheap follow-up.

Verdict: not clean — 2 High, 7 Medium open.
