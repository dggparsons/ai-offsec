# Round 2 — end-user lens (reviewer-end-user, 2026-11-03 ~22:30 UTC)

Walked http://localhost:3000 + http://localhost:8000 + read-only DB (docker compose exec psql)
as Dave (UK morning reader). Digest snapshot under test: `generated_at 2026-11-03T22:25:31Z`,
window 24 h. Verified every claimed fix from `_project/review/round-1-response.md` against live
data; did not trust tags or counters.

## Findings

| # | Severity | Where | Problem | Evidence (live) | Status |
|---|---|---|---|---|---|
| 1 | High | Digest top 10, item #9 (also "Exploitation" section) | "October sponsors-only newsletter" is a paid-newsletter sales meta-post, not news and not AI/LLM-relevant. Whole body: "I sent out the October edition… Pay $10/month to stay a month ahead of the free copy! Tags: newsletter". It occupies a top-10 slot over eligible vLLM/Qwen items (see #2). | digest JSON #9 `simon-willison 0.7375`; body_text quoted from DB | open |
| 2 | High | Digest coverage / "Models & inference" section | Zero model/inference releases in today's digest although the window has vllm v0.33.0rc3 (0.905, ai_relevant, eligible), Qwen 3.8 27B local story (0.8775, eligible), llama.cpp b12072–b12079, ollama v0.40.14, llm 0.37. Both high scorers were excluded by the per-section cap (models full with 3 agent papers) while the list filled to 10 with lower-scored items — sponsors post 0.7375 and BlueLM CVE 0.7125 took slots. Pool backfill only fires on a short list, so it never rescued them. Round-1 #6/#7's fix created the inverse failure. | DB: `vllm-project/vllm v0.33.0rc3` 0.905; `Qwen 3.8 27B on my laptop…` 0.8775; digest sections: models = [praktor, Kerkoporta, StateGate] | open |
| 3 | High | /api/search?q=jailbreak and q=GLM-5.3 | Ranking leg of round-1 #9 is unchanged. "jailbreak" #2 = CVE-2021-2351 Oracle Database 2021 CVE — the term "jailbreak" does not occur in its body at all (`position('jailbreak' in lower(body_text)) = 0`), non-AI, priority 0.43. "GLM-5.3" #4 = Citrix NetScaler KEV CVE; Adobe ColdFusion KEV CVE #6. KEV backfill still outranks relevant items. (Snippet markup IS stripped now — that half of the fix works.) | live API results quoted; DB term-position query | open |
| 4 | Medium | Taxonomy on digest items #2, #3, #5, #9 | Labels that don't describe the item. ETUDE paper (#2) and EtE paper (#3): `mcp.security` though neither abstract mentions MCP (agent frameworks / web fraud vs coding agents). Kerkoporta (#5): `ai.model.release` though it is a backdoor-attack paper, no release. #9: `offsec.vulnerability` on a sponsorship note. | arXiv abstracts quoted from body_text; digest JSON taxonomy arrays | open |
| 5 | Medium | Digest #10 BlueLM Copilot TLDR/body | Technical identifier corrupted by markup stripping: stored text and TLDR say "crafted ACTIONSEND intent"; ground truth is "ACTION_SEND" ([Rapid7](https://www.rapid7.com/db/vulnerabilities/cve-2026-89229/), [CVE Tracker](https://trackcve.app/cve/CVE-2026-89229)). Body contains zero underscores anywhere — the cleaner eats them, so the corruption is systematic for `snake_case` terms. | digest #10 TLDR quoted; full body_text grep `_` = 0 matches | open |
| 6 | Medium | /events listing + search results: release titles | Release-title fix only works for rows ingested after ~22:35: `llama.cpp release b12080` (created 22:35) is human, but b12064–b12079, `vllm-project/vllm v0.33.0rc3: v0.33.0`, `ollama/ollama v0.40.14: v0.40.14` keep raw-tag titles, rendered live on /events ("ggml-org/llama.cpp b12079: b12079") and in search snippets. Rescore does not re-derive titles for existing rows. | DB title/created_at listing quoted; /events HTML quoted | open |
| 7 | Low | Search snippets | vllm v0.32.0 snippet mid-word cut ("…answers choice, noul and score qu") with commit-log/issue-number boilerplate ("#53183"); "NVIDIA Cosmos Reason 2" (GLM-5.3 #2) has an empty snippet; digest #10 title carries a trailing space ("…component of BlueLM "). | /api/search?q=GLM-5.3 quoted | open |

## Verified fixed (spot-checked, passes)

- **arXiv ingestion (r1 #5):** source `arxiv-cscr` now has **38 events** (first seen today 05:00 UTC); 5 in the top 10. /sources shows it healthy with last fetch 22:19. RSS connector "raise on zero entries" path untestable without breaking the feed — accepted.
- **Digest list length (r1 #7):** 10 items, header "Today's ten".
- **Counters (r1 #8):** reconcile exactly at snapshot time. Recomputed from DB with the gate logic in `backend/app/api/digest.py:51-65`: window total 528 = 10 shown + 37 eligible-not-shown (eligible pool = 47 verified by SQL) + 481 suppressed. Apparent drift to 530 now is 2 late-ingested backdated items — snapshot is static by design.
- **Generic-CVE flood (r1 #1):** no GStreamer/Brotli/WordPress-style junk in the top 10; NVD bulk rows and HN are gated out of the digest (`digest_worthy`).
- **Headline/TLDR hygiene (r1 #3/#4, check 2):** all 10 titles human; TLDRs end on word boundaries with "…" or full stop; no commit logs; TLDRs are synthesised prose (8/10 clearly not body prefixes; praktor/Qwen-style extractive prefixes are already plain advisory prose). Caveat: finding #5.
- **Markdown on detail pages (r1 #12):** heuristic filler rows gone; page renders 6 LLM analyses per event. `&#x27;` in HTML source is single-escaped and renders as `'` in a browser — not a leak.
- **HN boilerplate (r1 #13):** HN items in /events have normal prose TLDRs.
- **en-GB dates (r1 #11):** "03/11/2026, 17:27" (24 h) everywhere checked; no AM/PM, no US MM/DD.
- **/sources footer (r1 #15):** no POST/PATCH/DELETE/admin hints. Page shows anthropic-news "disabled" honestly (r1 #16 mitigation via Simon Willison/DeepMind feeds is live — both have events).
- **emerging_themes (r1 #17):** entity-based (`repository:ggml-org/llama.cpp: 12`, `cwe:CWE-22: 2`…), not raw tag counts.
- **LLM analyses:** 281 rows `model='cockpit/kat8'` (fact_summary/technical_delta/significance kinds), rendered with model attribution on event detail pages; read as synthesised prose.
- **Backfill (r1 #10):** historic rows (KEV 2014, Chrome CVEs dated 2026-10-27 ingested tonight) stay searchable but out of the 24 h window and digest.

## Per-item verification (check 1 & 3, all 10, bodies read)

| # | Item | AI-relevant? | Taxonomy OK? |
|---|---|---|---|
| 1 | praktor Telegram path traversal | ✓ agent workspace/Claude agent | ✓ |
| 2 | ETUDE tool-update gap | ✓ | ✗ `mcp.security` (no MCP in paper) |
| 3 | EtE fraud vs coding agents | ✓ | ✗ `mcp.security` (no MCP in paper) |
| 4 | AgentCap capability auth | ✓ | ✓ (explicitly MCP) |
| 5 | Kerkoporta backdoors | ✓ | ✗ `ai.model.release` |
| 6 | StateGate prompt optimisation | ✓ | △ `offsec.vulnerability` a stretch |
| 7 | Stanza pickle RCE | ✓ AI software | ✓ (no ai.* tag, but labels accurate) |
| 8 | J-Anchor prefill-jailbreak defence | ✓ | ✓ |
| 9 | Sponsors-only newsletter | ✗ **not news, no AI content** | ✗ `offsec.vulnerability` |
| 10 | BlueLM Copilot path traversal | ✓ AI app | ✓ |

## Done-when results (PLAN.md checks)

1 **FAIL** (9/10 — finding #1) · 2 **FAIL** (finding #5 artefact; otherwise clean) · 3 **FAIL** (findings #4, #9-row) · 4 **FAIL** (findings #2; arXiv leg passes) · 5 **PASS** (all five pages 200 and useful; detail pages from listings fine) · 6 **PASS** (counters recompute exactly).

## Not checked

POST/PATCH blocking (probe forbidden); client-side JS interactivity; the RSS zero-entry failure path (would require breaking a live source).

Verdict: not clean — 3 High, 3 Medium.
