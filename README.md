# AI News — Real-Time Intelligence System

An intelligence fabric for offensive-AI and enterprise-AI-adoption developments.
It continuously collects public source material (advisories, vendor blogs,
model releases, MCP ecosystem changes, research, enterprise case studies),
normalises it into a canonical, versioned event schema, enriches it with
deterministic extraction plus local-LLM analysis, and delivers hybrid search,
dashboards, alerts, digests and a read-only MCP interface.

## Architecture

```
Official APIs / RSS ─┐
                     ├─► Ingestion connectors ─► Raw immutable store (SeaweedFS, S3 API)
Web / GitHub / Papers┘            │
                                  ▼
                          Event queue (Redis / arq)
                                  ▼
   Normalise → identifier/entity extraction → dedupe/change detection
                                  ▼
        Classification + relevance scoring → LLM analysis workers
                                  ▼
        Postgres (metadata + pgvector)  →  hybrid search / entity links
                                  ▼
        Dashboard · Slack/email alerts · REST API · read-only MCP
```

Three planes, per the design doc:

- **Collection plane** (`app/connectors`, `app/worker.py`) — source registry,
  poll schedules, conditional fetches (ETag/Last-Modified), immutable raw
  object storage keyed by content hash.
- **Intelligence plane** (`app/pipeline`) — normalisation, deterministic
  identifier extraction, taxonomy classification, dedupe, relevance scoring,
  LLM summarisation with evidence provenance, embeddings.
- **Delivery plane** (`app/api`, `app/mcp_server.py`, `frontend/`) — REST API,
  hybrid lexical+vector search, dashboard, alert queue, daily digest.

Raw material is stored immutably and separately from LLM-generated analysis;
every analysis row carries a `prompt_version` and the model label that wrote
it. Analysis rows are only stored when the LLM produced them — the heuristic
fallback writes a TLDR and nothing else, rather than filler prose.

## Daily digest

The front page is an editorial product, not a raw feed: only AI/LLM-relevant
events (`event.ai_relevant`, set by the classifier) above a 0.45 quality
floor, from sources trusted ≥0.5, with a per-section cap and backfill from
the eligible pool. Generic CVEs with no AI connection stay searchable but
never occupy the daily list, whatever their CVSS. Counters are truthful:
"eligible not shown" is reported separately from "suppressed below the bar".
A snapshot is archived per UTC day (07:03 run, or first view of the day).

## Quickstart

```bash
cp .env.example .env
docker compose up --build
```

Then:

- Dashboard: http://localhost:3000
- API docs (OpenAPI): http://localhost:8000/docs
- MCP server (streamable HTTP): http://localhost:8100/mcp
- SeaweedFS master UI: http://localhost:9333

Seed sources are inserted on first boot: CISA KEV, GitHub Advisories, NVD,
GitHub releases (llama.cpp/vLLM/Ollama, MCP spec), SecLists Full Disclosure,
Hacker News, arXiv cs.CR, and AI coverage feeds (OpenAI, Hugging Face,
DeepMind, Google AI, Google Security Blog, Trail of Bits, Simon Willison,
Embrace The Red). On later boots the seeder
inserts newly added seeds and corrects a seed's URL if it changed upstream;
operator edits to cadence/trust are never touched. The worker polls due
sources every minute; the first ingestion cycle runs immediately at startup.
On first contact with a source, items older than `BACKFILL_MAX_AGE_DAYS`
(default 30) are skipped so historic catalogues don't swamp the store.

To force a fetch of one source:

```bash
curl -X POST http://localhost:8000/api/sources/cisa-kev/fetch -H "x-api-key: $API_WRITE_KEY"
```

## LLM configuration

The system talks to any OpenAI-compatible endpoint. The default in
`.env.example` is the authenticated local model queue on the host
(`http://host.docker.internal:11435/v1`, model `cockpit/kat8`; the bare
Ollama port 11434 is retired). Point `LLM_BASE_URL` at vLLM, llama.cpp's
server, or a cloud provider instead. Embeddings use the same endpoint when
it serves an embedding model; the queue currently doesn't, so embeddings
fall back to the deterministic pseudo-hash mode described below.

With `LLM_ENABLED=false` (or when the endpoint is unreachable) the pipeline
falls back to deterministic heuristics: keyword taxonomy classification,
extractive summaries, and hash-based pseudo-embeddings. Everything still
works end-to-end; quality is just lower. This keeps external content out of
any model call unless you explicitly allow it.

## Layout

```
backend/
  app/
    config.py            settings (env-driven)
    db.py                async SQLAlchemy engine/session
    models.py            sources, events, entities, analyses, alerts, feedback
    schemas.py           canonical ingestion envelope (Pydantic)
    connectors/          base + cisa_kev, github_advisories, github_releases, nvd, rss, seeds
    pipeline/            normalize, dedupe, extract, classify, score, llm, embed, ingest, alerts
    search/hybrid.py     BM25-ish FTS + pgvector, reciprocal-rank fusion
    api/                 REST routes
    worker.py            arq worker: scheduler + fetch/process tasks
    mcp_server.py        read-only MCP tools over streamable HTTP
  tests/                 pytest: classifier, TLDR, scoring, digest gate
frontend/                Next.js dashboard (Priority Now, search, event detail)
```

## Trust model

- All fetched content is treated as hostile: raw bytes go to the object store
  untouched; text is sanitised before any LLM call; fetched text can never
  modify prompts, tool config, or workflow definitions.
- The MCP server exposes only narrow read-only tools (search, get_event,
  get_entity, recent changes, related CVEs, model releases, source evidence).
  No generic SQL, no URL fetcher, no file access.
- Analyst feedback (open/save/escalate/dismiss) is stored separately and will
  be used to learn relevance weights — see `app/pipeline/score.py`.

## Public deployment hardening

The API is exposed publicly via a named cloudflared tunnel
(`api.ai-offsec.com` → `localhost:8000`). Layers, edge inward:

1. **Cloudflare WAF custom rule** blocks every non-GET/HEAD/OPTIONS request to
   `api.ai-offsec.com` — mutations never reach the origin.
2. **Cloudflare rate limit**: 25 req / 10 s / IP on the API host.
3. **Backend write guard** (`app/main.py`): mutating requests require
   `x-api-key: $API_WRITE_KEY`; with no key configured, writes fail closed.
4. **Localhost binding**: all compose ports bind to `127.0.0.1`, so the stack
   is unreachable from the LAN; the only public path is the tunnel.
5. **CORS** restricted to the dashboard origins; GET-only methods.

The public frontend is built with `NEXT_PUBLIC_READ_ONLY=true`, which hides
analyst feedback controls. Run writes locally against `http://localhost:8000`
with the key, e.g.:

```bash
curl -X POST localhost:8000/api/sources/cisa-kev/fetch -H "x-api-key: $API_WRITE_KEY"
```


## Roadmap mapping (from the design doc)

| Doc milestone | Where it lands |
|---|---|
| Weeks 2–4 source registry + raw ingestion | `app/connectors`, `sources` table, SeaweedFS |
| Weeks 4–6 canonical schema, parsing, dedupe | `app/schemas.py`, `app/pipeline/{normalize,dedupe}.py` |
| Weeks 5–8 hybrid search | `app/search/hybrid.py` |
| Weeks 6–9 LLM extraction + summaries | `app/pipeline/llm.py`, `analyses` table |
| Weeks 8–10 relevance + alerts | `app/pipeline/score.py`, `alerts` table |
| Weeks 9–12 dashboard + watchlists | `frontend/` |
| Weeks 11–14 MCP/API | `app/mcp_server.py`, `app/api/` |
| Months 4–6 graph + trends | entity/event_entity tables seeded; graph UI not yet built |

Deliberately stubbed for later: SimHash/MinHash near-dupe detection, change
significance modelling, OpenCTI/MISP export, analyst-auth RBAC, entity-graph
and trend-clustering UI. Each has a marked extension point in the code.
