# Round 1 — end-user lens (reviewer-end-user, 2026-11-03 ~21:00 UTC)

Walked https://ai-offsec.com + https://api.ai-offsec.com + local stack + DB as Dave (morning reader).
Scratch copies of fetched HTML/JSON in the session scratchpad (daily.json, home.html, events.html).

## Findings

| # | Severity | Where | Problem | Evidence | Fix | Status |
|---|---|---|---|---|---|---|
| 1 | High | ai-offsec.com home, items #2–#5 | 4 of 7 "Today's ten" items are generic CVEs with no AI link | Arc = basekick-labs/arc (Go time-series DB, verified via GitHub API); Elo = npm @enspirit/elo (template compiler); .NET Brotli; GStreamer FLV | AI-relevance gate before the daily list | open |
| 2 | High | Item #4 taxonomy | Brotli .NET CVE tagged `ai.model.architecture` | digest JSON: taxonomy ["ai.model.architecture","enterprise.deployment","offsec.vulnerability"] | Fix tagger; regression tests with known non-AI CVEs | open |
| 3 | High | Item #6 | Title "ggml-org/llama.cpp b12077: b12077"; TLDR is commit-log dump, mid-sentence cut; tagged offsec.vulnerability | quoted on page | Synthesise release headlines; never emit raw changelogs; don't tag routine builds as vulns | open |
| 4 | High | Items #1,#5,#7 | Mid-word truncation, no ellipsis ("…BoundSubject fingerpri", "…path.Join, which ") | quoted | Word-boundary truncation with ellipsis | open |
| 5 | High | /sources: arxiv-cscr "ok" | arXiv has produced ZERO events ever; wrong feed URL returns empty channel; health still "ok" | export.arxiv.org/rss/cs.CR → 200, 0 items; rss.arxiv.org/rss/cs.CR → 139 items | Fix URL; health must reflect "0 items parsed for N fetches" | open |
| 6 | High | Digest coverage | HF "Transformers Model Integration Contracts" (0.58, in window, above floor) absent while the list had 3 empty slots; OpenAI security posts at 0.35 suppressed below WordPress CVEs at 0.73–0.97 | DB queries quoted in walkthrough | Rebalance scoring: boost AI, penalise generic CVE feeds | open |
| 7 | High | Home header | "Today's ten" shows 7 items; research/enterprise sections starve the cap | page text | Fill from eligible pool or count-aware header | open |
| 8 | High | Home counter | "402 lower-priority updates suppressed" irreconcilable (446−7=439≠402) and includes items scored up to 0.97, above displayed #7 at 0.63 | window query: 161 unshown items ≥0.45 floor incl. Welcart WP plugin CVE at 0.97 | Truthful split: below-floor vs eligible-not-shown | open |
| 9 | High | /api/search | "jailbreak" #2 = Oracle DB CVE-2021-2351; "GLM-5.3" top-5 = vllm release notes + Citrix CVE; snippets leak raw HTML/markdown; several empty | quoted | Strip markup before indexing/snippets; downweight KEV backfill; fix vector leg | open |
| 10 | Medium | Ingest backfill | Whole back-catalogues ingested (KEV 1716 incl. Shellshock 2014, OpenAI 1351, HF 898) polluting /events and search | DB samples | Cap backfill or filter historical from defaults | open |
| 11 | Medium | All pages | US date format for a UK user ("11/3/2026, 5:27:25 PM") | quoted | en-GB locale | open |
| 12 | Medium | /events/<id> | Raw markdown shown literally ("### Impact"); placeholder analyses ("Automated delta unavailable (heuristic mode)", "None identified (heuristic mode)"); fact summary duplicates extracted text | praktor detail page | Strip/render markdown; drop filler analysis rows | open |
| 13 | Medium | /events first item | HN TLDR is a metadata dump ("Article URL: … Points: 6 Comments: 0.") | quoted | Strip HN boilerplate | open |
| 14 | Medium | Taxonomy spot-check | AI items under-tagged (Stanza pickle RCE: no ai.* tag; all HF/OpenAI events taxonomy []) while non-AI over-tagged | DB samples | AI-package rules; tag blog posts | open |
| 15 | Medium | /sources public page | Advertises POST/PATCH admin endpoints on a GET-only public API | quoted footer | Remove admin hint from public page | open |
| 16 | Medium | anthropic-news | Core source disabled with zero events | /sources: "disabled" | HTML connector or alternative coverage | open |
| 17 | Medium | emerging_themes | Just raw tag counts dominated by offsec.vulnerability (353) | API output | Entity-based themes | open |
| 18 | Low | Home vs archive | "material developments" counter missing from home; nothing marks which items require action | quoted | Show counters; badge action items | open |
| 19 | Low | Items #4,#5,#7 | Cryptic "updated · v 3" badge | quoted | Plain wording | open |

## Done-when results
1 FAIL (4/7 non-AI) · 2 FAIL (b12077, commit dump, truncations) · 3 FAIL (Brotli, builds-as-vulns, empty blog taxonomy) · 4 FAIL (arXiv zero ever; eligible HF item absent) · 5 PASS (all pages 200, detail from each listing, bad UUID 404) · 6 FAIL (2/4 queries junk; raw markup snippets) · 7 PARTIAL (one day exists; system is one day old; re-check tomorrow) · 8 FAIL ("ten"=7; suppressed count untrue).

## Not checked
POST/PATCH blocking on the public API (probe forbidden); client-side JS behaviour; local content parity beyond 200s.

Verdict: not clean — 9 High, 8 Medium.
