# Round 1 — fix response (2026-11-03)

Every High and Medium from the four round-1 reports, its disposition, and
the root-cause fix. Lows fixed where cheap; the rest listed at the end.

## facts

| # | Sev | Disposition |
|---|---|---|
| 1 | High | Fixed. Seed URL → `https://rss.arxiv.org/rss/cs.CR` (canonical per arXiv docs). Root cause beyond the URL: the RSS connector never noticed a zero-item feed — it now raises on `bozo`-with-no-entries and on 0 entries, so this failure mode shows in source health instead of hiding (standards #3). `seed_sources` is now a sync: it inserts new seeds and corrects changed seed URLs on boot, resetting stale validators — seed-file fixes now reach the live registry. |
| 2 | High | Fixed. Seed URL → `https://blog.google/security/rss/`; same seed-sync path applies it. |
| 3 | Medium | Fixed. README says SeaweedFS (S3 API) everywhere (also consistency #12, standards #8). |
| 4 | Medium | Fixed. `X-GitHub-Api-Version: 2026-03-10` in both GitHub connectors. |
| 5 | Medium | Fixed. Advisories connector paginates Link-header cursors, `sort=updated&direction=asc`, `per_page=100`, bounded at 5 pages/poll; the cursor only advances to items actually seen. |
| 6 | Medium | Fixed. NVD connector pages `startIndex` to `totalResults` (bounded 5 pages/poll, 7 s pacing without an API key); the next poll resumes from the last seen item instead of skipping. |
| 7 | Low | Fixed earlier in the round: `s3_access_key/secret` defaults now `any`. |

Coverage gaps: added the four verified feeds — Simon Willison, Embrace The Red,
Google DeepMind, Google AI — as P1 seeds. These also carry Anthropic news
(end-user #16) until an HTML connector exists.

## consistency

| # | Sev | Disposition |
|---|---|---|
| 1 | High | Fixed. `rescore_events` uses `source.trust_score`, preserves corroboration from stored score components. It still runs on worker boot, deliberately: it's now a full re-classify/re-gate/re-score maintenance pass (idempotent) so pipeline changes propagate to the back catalogue — that is how these fixes reach existing rows. |
| 2 | High | Fixed. Quickstart curl carries `x-api-key: $API_WRITE_KEY`. |
| 3 | High | Fixed. Releases connector derives `source_type` from the registry row and taxonomy from `source.config["taxonomy"]` / source_type (`specification` → `mcp.specification`). |
| 4 | High | Fixed. New digest section "Safety, jailbreaks & evals" (`ai.safety`, `ai.evaluation`) + both added to `INTEREST_BOOST`. |
| 5 | High | Fixed. `\bexploit\b` replaced with publication-shaped patterns (`exploit code/module/poc/…released`, `proof-of-concept`, exploit-db, metasploit); `"poc" in body` → word-bounded regex (`epoch`/`pocket` can't match). Regression tests pin all of these. |
| 6 | High | Fixed. `find_model_releases` uses JSONB containment (`contains` per label, OR'd) instead of ARRAY `.overlap` on a JSON column. |
| 7 | Medium | Fixed by rewrite. Dead inner loop deleted; gating is now section-independent and mission-first: `ai_relevant` + trust + non-bulk-source. The old per-section PoC gate is gone intentionally — the AI-relevance gate is the stricter, correct invariant (an AI-software advisory without a public PoC is still news for this reader; a generic CVE with a PoC is not). |
| 8 | Medium | Fixed. Classifier rules added for `ai.model.weights`, `research.benchmark`, `offsec.tradecraft`. |
| 9 | Medium | Fixed. FeedbackButtons checks `res.ok` and reports rejection instead of showing ✓; compose sets `NEXT_PUBLIC_READ_ONLY=true` (this stack is what the tunnel serves), matching the README claim. |
| 10 | Medium | Fixed. Dead `scheduler_interval` setting deleted. |
| 11 | Medium | Fixed. Write guard reads `settings.api_write_key` (pydantic Settings, which loads `.env`) instead of a bare `os.environ` lookup. |
| 12 | Medium | Fixed with facts #3. |
| 13 | Medium | Fixed. One canonical `ALLOWED_LABELS` in classify.py; classifier `existing=`, LLM merge, and prompt all validate against it. Test: unknown labels are dropped. |
| 14 | Medium | Fixed. Taxonomy filters standardised on `cast(..., JSONB).contains` in events.py and hybrid.py; mcp_server fixed under #6. |
| 15 | Medium | Fixed. Dashboard renders `emerging_themes` (now entity-based, see end-user #17) and labels each top item with its section. |
| 16–21 | Low | All fixed: `quanti[sz]`, Reddit mention dropped (docstring now says HN only), digest uses `settings.alert_threshold` for "requires action", en-GB locale across all pages, layout lists seeds/alerts/tests, archive wording corrected. |

## standards

| # | Sev | Disposition |
|---|---|---|
| 1 | High | Fixed. Worker counts per-envelope failures; all-failed ⇒ failure (back-off engages), partial ⇒ logged and reported. |
| 2 | High | Fixed. Releases connector logs per-repo failures, raises when every watched repo fails; false comment removed. |
| 3 | Medium | Fixed with facts #1 (RSS connector fails loudly on bozo/zero-entry feeds). |
| 4 | Medium | Fixed. `evidence_event_ids=[]` — no more circular self-citation; provenance lives in `raw_object_uri`/hashes. |
| 5 | Medium | Fixed. LLM output validated against `AnalysisOut` (pydantic): extra keys dropped, confidence pattern-checked and defaults to `low`, labels filtered to `ALLOWED_LABELS`, kinds iterated from `ANALYSIS_KINDS` only. |
| 6 | Medium | Fixed. `_endpoint_is_local` parses with `urlsplit` and compares the hostname exactly. |
| 7 | Medium | Fixed. `backend/tests/` (22 tests): classifier regressions, TLDR/markup hygiene, PoC scoring, digest gate. Run: `pip install -e '.[dev]' && pytest`. |
| 8 | Medium | Fixed with facts #3. |
| 9 | Medium | Fixed with consistency #10. |
| 10–13 | Low | Fixed: graph UI moved to the stub list, compose DB password parameterised (`${POSTGRES_PASSWORD:-intel}`) and stale minio defaults dropped, LLM fallback passes taxonomy through, dead loop deleted. |

## end-user

| # | Sev | Disposition |
|---|---|---|
| 1 | High | Fixed. `Event.ai_relevant` column + `is_ai_relevant()` gate (AI-dedicated source types, ai.*/mcp.* taxonomy, or word-bounded AI-term match). Digest hard-gates on it; scoring adds +0.10/−0.25 so alerts and orderings agree. |
| 2 | High | Fixed. Classifier rules rewritten narrow (see consistency #5); regression tests pin the Brotli/GStreamer cases. |
| 3 | High | Fixed. Release titles are human headlines (`llama.cpp release b12077`, never `b12077: b12077`); TLDR path strips markup/boilerplate and truncates on word boundaries; release builds no longer match `offsec.vulnerability` (rule needs CVE/CVSS/vulnerabilit/RCE-shaped text, and `normalize` strips commit-log boilerplate first). |
| 4 | High | Fixed. `truncate_words` — word-boundary cut with `…`, used by both TLDR paths and LLM output validation. |
| 5 | High | Fixed with facts #1 + standards #3: correct URL, and a zero-item feed is now a visible failure, not "ok". |
| 6 | High | Fixed. `ai_relevant` boost/penalty in scoring plus the digest gate and pool backfill: sections that starve no longer shrink the list — remaining slots fill from the eligible pool. |
| 7 | High | Fixed with #6 (fill from eligible pool to TOP_N when the pool allows). |
| 8 | High | Fixed. Counters split truthfully: `eligible_not_shown` vs `suppressed_low_priority` (below floor or off-mission); dashboard shows all four counters. |
| 9 | High | Fixed. Snippets pass through `strip_markup`; markdown/boilerplate stripping moved into `normalize.clean_text`, so every newly stored body — and the search index built from it — is plain prose. Rescore re-cleans stored bodies and re-indexes. |
| 10 | Medium | Fixed. `backfill_max_age_days` (default 30): first-sight items older than the window are skipped unless they corroborate an existing event. Existing historic rows remain searchable by design ("everything stays searchable") but age out of every default view. |
| 11 | Medium | Fixed. en-GB everywhere. |
| 12 | Medium | Fixed. Heuristic filler rows ("Automated delta unavailable…") are no longer written and all existing `model='heuristic'` rows are deleted by rescore; body text is markup-stripped at normalisation. |
| 13 | Medium | Fixed. HN boilerplate lines (`Article URL`, `Points:`, `Comments:`) stripped at normalisation; test pinned. |
| 14 | Medium | Fixed. AI-package names (stanza, comfyui, gradio, whisper…) added to the relevance terms; AI-dedicated source types (`vendor_blog`, `research`, `repository_release`, `specification`) are relevant by construction; classifier covers benchmark/weights/safety labels blog posts carry. |
| 15 | Medium | Fixed. Public /sources footer no longer advertises admin endpoints. |
| 16 | Medium | Mitigated. Anthropic still has no RSS (facts verified); Simon Willison + DeepMind/Google AI feeds cover their releases until an HTML connector exists. |
| 17 | Medium | Fixed. `emerging_themes` is entity-frequency over AI-relevant events in the window, not raw tag counts. |
| 18–19 | Low | Fixed: "requires action" badge on cards ≥ alert threshold, material-developments counter on the dashboard, `updated · version N` wording. |

## LLM (root cause: never ran once)

`.env` pointed at the retired Ollama port 11434 with an empty key. Now:
`LLM_BASE_URL=http://host.docker.internal:11435/v1` (the authenticated local
queue, verified live today), `LLM_MODEL=cockpit/kat8`, `LLM_API_KEY` set.
LLM analysis is also now spend-aware: it only runs for mission-relevant or
≥0.7-priority events, retries 503s with doubling backoff (3 attempts), and
schema-validates output. The queue serves no embedding model
(`--embedding-model` not configured) — embeddings fall back to the
documented pseudo-hash mode, so semantic search recall stays weak until an
embedding model is added to the queue; lexical search is unaffected.

## Deferred / accepted

- Existing pre-cap historic rows (KEV 2014 etc.) remain in the store and
  searchable; they're excluded from the digest and all default views. A
  one-off purge is a destructive call for the owner.
- `scheduler_interval` was deleted rather than wired (single hardcoded cron
  is the actual behaviour; a flag nobody used is worse than no flag).
- Round-2 verification should specifically re-walk: today's digest section
  mix, arXiv event count > 0, LLM-produced analysis rows
  (`model='cockpit/kat8'`), and search snippets.
