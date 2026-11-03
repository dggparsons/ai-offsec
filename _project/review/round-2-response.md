# Round 2 — fix response (2026-11-03)

Round 2 ran four fresh lenses against the fixed product. Reports:
`round-2-facts.md`, `round-2-consistency.md`, `round-2-standards.md`,
`round-2-end-user.md`. Combined: 5 High, 11 Medium. All fixed at root cause
and re-verified live; dispositions below.

## facts (0 High, 1 Medium)

| # | Sev | Disposition |
|---|---|---|
| 1 | Medium | Fixed. `.env.example` now ships the live queue (`host.docker.internal:11435`, `cockpit/kat8`, key required) and `PROCESSING_VERSION=0.2.0`; README's LLM section and seed list updated to match. |
| — | Low | Accepted: `anthropic-news` stays in the registry, disabled, until an HTML connector exists (Simon Willison covers Anthropic meanwhile). |

## standards (0 High, 3 Medium)

| # | Sev | Disposition |
|---|---|---|
| 1 | Medium | Fixed. New tests: write guard (fail-closed, wrong key, PUT/DELETE, reads open), digest floor/cap/backfill/swap via extracted `eligible()`/`select_top()`, AnalysisOut validation (extra keys dropped, bad confidence rejected, no upward default). 38 tests, all green in-container. |
| 2 | Medium | Fixed. NVD cursor now advances to `now` only when the whole window was paged; otherwise it resumes from the last item seen. The dead `last_modified_seen` variable is the cursor. |
| 3 | Medium | Fixed with facts #1 (.env.example + README endpoint docs). |
| — | Lows | Fixed the cheap ones: per-item raw bytes in NVD/advisories (no more shared page evidence), CISA zero-entry feed fails loudly, stale seeds.py/normalize docstrings corrected. Accepted: weak default DB password (localhost-bound, parameterised), `fromtimestamp` guard. |

## end-user (3 High, 3 Medium)

| # | Sev | Disposition |
|---|---|---|
| 1 | High | Fixed. Content floor: narrative sources (blogs, papers, forums) need ≥200 chars of body to be digest-eligible — the paywalled "October sponsors-only newsletter" stub is out. Test pinned. |
| 2 | High | Fixed. `select_top` rewritten: the per-section cap is now a diversity guard with score-based swap-in — an excluded item that outscores the weakest included one takes its place. Test pinned. (The reviewer's specific example, vLLM v0.33.0rc3, was actually outside the 24 h window — published 02 Nov 10:10 — but the flaw it exposed was real.) |
| 3 | High | Fixed, two root causes. (a) All 6,375 stored embeddings were pseudo-hash junk (the endpoint never served embeddings) — nulled; pseudo fallbacks now store NULL so the semantic leg stays honest instead of ranking noise. (b) Search ranking now fuses RRF with priority (×10/×0.2), so "jailbreak" returns prompt-injection/LLM-safety papers and "GLM-5.3" returns vLLM/llama.cpp releases — verified live. |
| 4 | Medium | Fixed. Emphasis-stripping regex was eating underscores in snake_case identifiers (`ACTION_SEND` → `ACTIONSEND`); now boundary-aware. Regression test pinned; rescore re-cleaned all stored bodies. |
| 5 | Medium | Fixed. `ai.model.release` requires release-shaped verbs ("rolling release model" VulDB boilerplate no longer tags a PHP classroom CVE as AI). Regression test pinned. |
| 6 | Medium | Fixed. Rescore retitles legacy raw release titles ("org/repo b12077: b12077" → "llama.cpp release b12077", including tag-prefix variants); 13 stragglers from round-2-consistency covered by the broadened pattern. |

## consistency (2 High, 4 Medium)

| # | Sev | Disposition |
|---|---|---|
| 1 | High | Fixed (pre-report, same evening): NVD and GitHub-advisories envelopes carry per-item JSON bytes, not the last page's. Historical consequence (1,494 NVD events sharing 28 content hashes) self-heals: next poll produces distinct per-item hashes, one version bump each, then stable. |
| 2 | High | Fixed. The unbounded backfill was the stale pre-fix worker (no hot-reload) running old code before its 22:18 restart. The 30-day cap was already in; the two empty-title `-infinity` junk rows it created are deleted, and the RSS connector now skips content-free entries so the class can't recur. |
| 3 | Medium | Fixed with standards #2 (NVD cursor). |
| 4 | Medium | Fixed. Rescore preserves LLM-contributed labels for events with a real LLM analysis (validated against ALLOWED_LABELS); heuristic-only events get a clean re-classify. Measured regression (82→0) cannot recur. |
| 5 | Medium | Fixed. HF's feed ships 896/896 entries title-only (verified). The RSS connector now fetches the article page for recent title-only entries (≤25/poll, inside the backfill window) and — critically — swaps `raw_content` to the page bytes so change detection sees the new body (first version of this fix silently discarded pages as "unchanged"; caught on live verify). 25 HF articles now have full bodies and LLM TLDRs; "Transformers Model Integration Contracts" — the exact item round-1 flagged as missing — is in today's digest. |
| 6 | Medium | Fixed. `litellm`/`mlflow`/`tensorrt` added to the AI-relevance terms (LiteLLM KEV entries now gate correctly). |
| — | Lows | Accepted with notes: `eligible_not_shown` reads from a 300-row candidate window (cosmetic bound); the "requires action" badge threshold is 0.75 hardcoded in the frontend (= current `ALERT_THRESHOLD`); `mcp.client`/`mcp.enterprise` remain LLM-only labels by design. |

## Live verification after all round-2 fixes

- Digest (re-snapshotted): 10/10 AI-relevant — agent-workspace CVE, 5 agent-security papers, SurrealDB MCP authn CVE, NN-weights protection paper, Stanza pickle RCE, 2 Hugging Face items with real bodies and synthesised TLDRs. Counters reconcile.
- Search: "jailbreak" → prompt-injection research; "GLM-5.3" → vLLM/llama.cpp releases. Snippets plain prose, TLDR fallback for title-only records.
- 38 backend tests pass; they discriminate (standards reviewer proved a doctored suite fails).
- Write guard 403s anonymous/wrong-key writes; reads open; public site serves the fixed digest through the tunnel.
