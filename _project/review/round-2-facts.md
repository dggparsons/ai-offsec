# Round 2 — facts/sources lens (reviewer-facts, 2026-11-03)

Hostile re-verification of round-1-response.md claims. All URLs fetched live
2026-11-03 (curl, UA `ai-news-intel/0.1`); all DB queries via
`docker compose exec -T db psql -U intel -d intel`. Stack was up
(db/redis/seaweedfs 10 h, backend/worker/mcp/frontend freshly rebuilt ~8 min).

## Verified true (live evidence 2026-11-03)

- **Response facts #1 (arXiv)**: DB `sources.url` for `arxiv-cscr` is
  `https://rss.arxiv.org/rss/cs.CR` (seed-sync applied). Feed fetched live:
  200, final URL unchanged, 139 `<item>`s today. `events` joined to the
  source: **38 rows**, latest fetch 2026-11-03 22:24 UTC. Claim fully verified.
- **Response facts #2 (Google Security Blog)**: registry URL is
  `https://blog.google/security/rss/`. Live: 200, 20 items, newest 21 Oct
  2026; the blog HTML index shows nothing newer, so the feed matches the
  blog's own cadence (weekly-ish) — live and current. 30 events in DB, fetched
  today. Note: the feed's lastBuildDate/newest item is identical to what round 1
  saw on the same day (21 Oct) — it has not published since; not staleness.
- **Response facts coverage additions**: all four new seeds have events and
  fetched today — simon-willison 30 (feed: 30 items, newest 2026-11-03T16:29Z),
  embrace-the-red 231 (feed newest 13 Oct 2026 = the blog's own newest post
  per embracethered.com/blog/ HTML datetimes — quiet blog, not a stale feed),
  deepmind-blog 100 (feed serves gzip; 100 items, newest 2026-11-03T17:01Z),
  google-ai-blog 20 (newest 02 Nov 2026).
- **Response facts #4 (GitHub API version)**: code has
  `X-GitHub-Api-Version: 2026-03-10` at backend/app/connectors/github_advisories.py:24
  and github_releases.py:28. docs.github.com/en/rest/about-the-rest-api/api-versions
  (fetched today) lists 2026-03-10 as supported ("End of support: not yet
  scheduled"); 2022-11-28 supported until 2028-03-10. Live API:
  `GET api.github.com/advisories` with the header → 200 plus response header
  `x-github-api-version-selected: 2026-03-10`. Correct and current.
- **Response facts #5 (advisories pagination)**: code now does
  `per_page=100, sort=updated, direction=asc`, follows `resp.links["next"]`
  (bounded 5 pages), and the `modified` cursor advances only to the newest
  item actually seen. Matches the claim.
- **Response facts #6 (NVD paging)**: nvd.py uses `startIndex` paging and reads
  `totalResults` (lines 53, 60). Claim corroborated in code.
- **Response facts/standards #3 (RSS fails loudly)**: rss.py:31-36 raises on
  bozo-with-no-entries and on 0-entry feeds.
- **README quickstart**: `.env.example` exists; `docker compose up --build` is
  valid; all four documented endpoints live — :3000 → 200, :8000/docs → 200,
  :8100/mcp → 400-without-init (endpoint present, streamable-HTTP MCP),
  :9333 → 200 (SeaweedFS master UI). Ports match compose exactly
  (127.0.0.1 bindings). No "minio" string anywhere in README.md,
  backend/app/config.py, or .env.example. Every path named in the README
  Layout block exists on disk, including all connectors/, pipeline/, api/,
  tests/ entries. `frontend/ Next.js dashboard` is accurate: compose runs
  `npm run dev` = `next dev` (next ^15.1.0); the vinext scripts are opt-in
  alternates on port 3001.
- **All 16 seed URLs live**: cisa.gov catalog 200; github.com/advisories 200;
  nvd.nist.gov 200; github.com 200 (→ `/`); modelcontextprotocol.io 200
  (homepage 302s to current docs intro — benign); all RSS feeds above plus
  trailofbits (newest 03 Nov), seclists (02 Nov), hnrss (03 Nov 21:51Z),
  huggingface (896 items, 03 Nov 17:15Z), openai (1354 items, 03 Nov 12:00Z),
  arXiv (139 items, today). No dead, stale, or mis-redirected seed.
- **Compose vs README**: services db, redis, seaweedfs, backend, worker, mcp,
  frontend all defined and running; port mappings match README one-to-one.

## Findings

| # | Severity | File:line | Problem | Evidence (checked 2026-11-03) | Fix | Status |
|---|---|---|---|---|---|---|
| 1 | Medium | .env.example:6-9 (and README.md:85-88 echoing it) | Documented default LLM endpoint is dead: `.env.example` still ships `LLM_BASE_URL=http://host.docker.internal:11434/v1` with empty key and `LLM_MODEL=gpt-oss:20b`. Round-1 response says port 11434 is the *retired* Ollama port and the working endpoint is 11435 — but only `.env` was updated; the file the quickstart tells users to copy (`cp .env.example .env`) still points at the retired port. Fresh installs silently degrade to heuristic fallback | `curl localhost:11434/v1/models` → 000 (dead); `curl localhost:11435/v1/models` → 401 (live, authenticated queue); `.env` (live) uses 11435 + `cockpit/kat8`; `.env.example` unchanged | Update `.env.example` to the working endpoint shape (11435 + key placeholder + cockpit/kat8, or a commented Ollama block) | open |
| 2 | Low | DB `sources` row slug=`anthropic-news` (not in backend/app/connectors/seeds.py) | Live registry still contains an `anthropic-news` source at `https://www.anthropic.com/rss.xml` with trust_score 0.95 — a URL that 404s. Contradicts round-1's verified fact and the seeds.py:186 comment ("Anthropic publishes no public RSS"). Row failed once today (12:44 UTC) and is now `enabled=f`, 0 events; seed-sync inserts/corrects but never prunes dead rows, so it lingers and would break if re-enabled | Live fetch anthropic.com/rss.xml → 404; DB: enabled=f, last_success_at NULL, consecutive_failures=1, 0 events | Delete the row (or leave disabled but documented); make seed-sync prune registry rows whose URL is known-dead | open |
| 3 | Low | README.md:68-70 | Seed-source summary omits six of the sixteen seeds: seclists-fulldisclosure (a P0!), hn-frontpage, and the four round-1 coverage-gap feeds (simon-willison, embrace-the-red, deepmind-blog, google-ai-blog). Reader cannot discover the new coverage from the README | DB lists 17 sources (16 seeds + anthropic-news); README names 6 groups | Extend the parenthetical to list all seed families, or point at /sources | open |

## Notes on round-1-response.md honesty

All seven enumerated round-1 facts claims check out against live evidence and
code. The two items the response doc flagged for round-2 re-walking that fall
under this lens: arXiv events > 0 (38 ✓) and seed-URL correctness (all live,
registry URLs match seeds.py ✓). The response doc's own "Deferred/accepted"
section already discloses the missing embedding model; finding 1 above is the
part it did not disclose — the documented defaults (`.env.example`/README LLM
section) still describe the pre-move setup.

## Not checked

- Digest section mix, LLM-produced analysis rows (`model='cockpit/kat8'`),
  search snippets (assigned to other lenses; LLM row spot-check only via the
  response doc's claim).
- Whether the 11435 queue actually serves `cockpit/kat8` (401 without key;
  auth'd verification out of scope for facts lens).
- Feed-change detection (ETag/Last-Modified) behaviour per connector.

Verdict: not clean — 0 High, 1 Medium
