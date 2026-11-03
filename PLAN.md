# AI News (ai-offsec.com) – Plan

Purpose: Dave logs in every morning and reads the important local-LLM and AI-security news:
new model releases, models doing bad things (incidents, misuse), AI pentest methodology,
MCP/agent security. The current daily top-10 is dominated by irrelevant generic CVEs and
raw release-tag noise. This plan covers a hostile QA review of the live product
(https://ai-offsec.com, API https://api.ai-offsec.com) and fixing what it finds.

## Phases
| Phase | Goal | Exit gate | Status |
|---|---|---|---|
| 1 Review round 1 | Four independent reviewer lenses on live site + code | Findings saved in `_project/review/round-1-*.md` | done |
| 2 Fix | Every High and Medium fixed at root cause, same fault searched for elsewhere | `_project/review/round-1-response.md` written; stack rebuilt and digest regenerated | done |
| 3 Review round 2 | Fresh reviewer pass over the fixed product | A full round finds no High or Medium | done |

## Tasks
| ID | Phase | Task | Done when (testable) | Depends on | Status |
|---|---|---|---|---|---|
| T1 | 1 | End-user walkthrough of live site as Dave | Findings table saved | — | done |
| T2 | 1 | Cross-file consistency review | Findings table saved | — | done |
| T3 | 1 | Facts/sources review (feeds, URLs, README claims) | Findings table saved | — | done |
| T4 | 1 | Standards review vs ~/.claude/CLAUDE.md | Findings table saved | — | done |
| T5 | 2 | Fix all High/Medium at root cause | Each done-when check below passes against the regenerated digest | T1–T4 | done |
| T6 | 3 | Re-run reviewer lenses on fixed work | No High or Medium in round 2 | T5 | done |

## Done-when checks for the product (used by every reviewer)
1. Every item in today's top list is relevant to AI/LLM: models, agents, MCP, inference engines, AI-assisted offence/defence, AI pentest methodology, or a vulnerability in AI software. No generic CVEs with no AI link (e.g. GStreamer FLV, .NET Brotli).
2. Every listed item has a human-readable headline and a plain-prose TLDR: no raw version tags as titles (e.g. "ggml-org/llama.cpp b12077: b12077"), no commit logs, no markdown artefacts, no mid-word truncation.
3. Taxonomy labels shown on an item describe that item (spot-check 10; e.g. a Brotli CVE must not carry `ai.model.architecture`).
4. Coverage: when a new model release or AI-security paper exists in the window (Hugging Face, OpenAI, arXiv), it is represented in the digest; arXiv ingestion actually produces events.
5. All five nav pages (Dashboard, Events, Search, Archive, Sources) render useful content at ai-offsec.com without errors.
6. README matches live behaviour (domains, endpoints, source list).

## Decisions for Dave
| # | Decision | Recommended default | Status |
|---|---|---|---|
| 1 | offensive-ai.com serves a parked lander, not this app (ai-offsec.com is live). Attach it or stop referring to it? | Attach offensive-ai.com to the same Cloudflare site as ai-offsec.com | open |

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Fixes require re-scoring/re-tagging existing DB rows | High | Digest still wrong after code fix | `rescore_events` worker task exists; extend it to re-classify, then re-snapshot digest |
| LLM endpoint disabled/unreachable so heuristic path dominates quality | Medium | TLDRs stay extractive | Verify `LLM_ENABLED` and endpoint health as part of the fix round |

## Log
- 2026-11-03: Round 1 started. Evidence gathered: live top-10 contains 5 non-AI CVEs; "Today's ten" shows 7 items; arXiv source ingested 0 events; openai-news holds 1,351 events (suspected dedupe fault); llama.cpp release titled "b12077: b12077". Four reviewers briefed.
- 2026-11-03: Round 1 complete (4 reports in `_project/review/`). All High/Medium fixed at root cause; response in `_project/review/round-1-response.md`. Verified live: LLM analyses now written by cockpit/kat8 (was zero, ever); arXiv ingesting; regenerated digest is all-AI (praktor agent-workspace CVE, five agent-security papers, Stanza pickle RCE, BlueLM Copilot CVE); 22 backend tests green. Round 2 reviewers launched.
- 2026-11-03: Round 2 complete: 5 High + 11 Medium across the four lenses, all fixed at root cause and re-verified live (response in `_project/review/round-2-response.md`). Notable: pseudo-hash embeddings nulled (semantic leg was ranking noise), search fuses priority with RRF, HF title-only feed now fetches article pages, select_top cap swaps in outscoring items, "rolling release model" false positive killed. 38 tests green. Phase 3 exit gate met.
