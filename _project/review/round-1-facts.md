# Round 1 — facts/sources lens (reviewer-facts, 2026-11-03)

All URLs fetched live 2026-11-03. WebFetch auto-upgrades http→https, noted where relevant.

## Findings

| # | Severity | File:line | Problem | Evidence (checked 2026-11-03) | Fix | Status |
|---|---|---|---|---|---|---|
| 1 | High | backend/app/connectors/seeds.py:131 | `http://export.arxiv.org/rss/cs.CR` is the legacy host: returns a well-formed feed with ZERO `<item>` elements, so fetches "succeed" while ingesting nothing (matches DB: 0 events ever) | export.arxiv.org/rss/cs.CR: 200, no items, lastBuildDate 03 Nov 2026. rss.arxiv.org/rss/cs.CR: 200, ~47+ items same day. arXiv docs (info.arxiv.org/help/rss.html): canonical base is `https://rss.arxiv.org/rss/` | Change URL to `https://rss.arxiv.org/rss/cs.CR` (feed skips weekends; 14400 s polling fine) | open |
| 2 | High | backend/app/connectors/seeds.py:69 | Google Security Blog feed is ~6 months stale: blog moved to blog.google | Feedburner redirect feed: newest entry 23 Apr 2026. security.googleblog.com now 301 → blog.google/security/. New feed `https://blog.google/security/rss/`: 200, newest 21 Oct 2026 | Change URL to `https://blog.google/security/rss/` | open |
| 3 | Medium | README.md:14,32,135 | "MinIO/S3" vs actual SeaweedFS stack (compose runs chrislusf/seaweedfs; README:54 itself says SeaweedFS) | docker-compose.yml:30-38 | Replace with "SeaweedFS (S3 API)" | open |
| 4 | Medium | github_advisories.py:24, github_releases.py:24 | `X-GitHub-Api-Version: 2022-11-28` superseded; latest is 2026-03-10; old version supported until 2028-03-10 then 410 Gone | docs.github.com api-versions page, fetched today | Plan bump to 2026-03-10; re-test `modified` param | open |
| 5 | Medium | github_advisories.py:30-33,45,68 | Single page (per_page=50), no Link-header cursor following, no sort pinned; >50 advisories modified between polls are permanently skipped because modified_cursor jumps to newest seen | GitHub docs: `before`/`after` cursors, `sort`, `direction`, per_page max 100 | `sort=updated&direction=asc`, follow `after` cursor until exhausted | open |
| 6 | Medium | nvd.py:38-43,87 | resultsPerPage=100, no startIndex paging, cursor jumps to now — windows with >100 modified CVEs silently drop the rest (NVD bulk re-scores routinely exceed this) | Live API: totalResults 418608 with paging fields | Loop startIndex until totalResults before advancing cursor | open |
| 7 | Low | config.py:11-12 | `minio`/`minio12345` leftover defaults after SeaweedFS switch | compose overrides with `any` | Neutral defaults | open |

## Verified clean (each with live evidence 2026-11-03)
- hnrss.org/frontpage, blog.trailofbits.com/feed/, seclists.org/rss/fulldisclosure.rss, huggingface.co/blog/feed.xml, openai.com/news/rss.xml — all 200, current-day/recent entries.
- seeds.py "Anthropic publishes no public RSS (verified 2026-11)" — still true today (anthropic.com/rss.xml 404; only unofficial scraped feeds exist).
- CISA KEV JSON URL current (catalogVersion 2026.11.03, count 1767; all fields connector reads present). NVD 2.0 endpoint current. GitHub advisories/releases endpoints and params documented-correct (apart from #4/#5).
- README: gpt-oss:20b and nomic-embed-text exist on Ollama (768-dim matches EMBED_DIM); all ports/paths in quickstart match compose and code; all layout/roadmap paths exist.

## Coverage gaps (mission: new models, AI pentest methodology, model misuse, MCP/agent security)
Only OpenAI News + HF blog could have carried "new model" news; nothing covers DeepMind/Google AI, Meta, Mistral, Qwen; nothing is AI-pentest-specific. Verified working candidates (fetched today):
1. Embrace The Red — https://embracethered.com/blog/index.xml (newest 13 Oct 2026; prompt-injection/agent-security research — closest fit for AI pentest methodology)
2. Simon Willison — https://simonwillison.net/atom/everything/ (newest 03 Nov 2026; fastest independent model-release + prompt-injection coverage)
3. Google DeepMind — https://deepmind.google/blog/rss.xml (newest 03 Nov 2026)
4. Google AI blog — https://blog.google/technology/ai/rss/ (newest 02 Nov 2026)
Checked and NOT usable: ai.meta.com/blog/rss/ 404; mistral.ai/feed.xml 404; qwenlm.github.io feed stale (Sep 2025); msrc.microsoft.com/blog/rss not a feed; Anthropic none.

## Not checked
- Whether OpenAI/Cloudflare/hnrss rate-limit the connector's own UA (`ai-news-intel/0.1`).
- Exact accepted format of the `modified` range value on GET /advisories.
- Repo slugs via live API (format-checked only); Cloudflare WAF/tunnel state.

Verdict: not clean — 2 High, 4 Medium.
