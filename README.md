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
                     ├─► Ingestion connectors ─► Raw immutable store (MinIO/S3)
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
every analysis row carries `evidence_event_ids` and a `prompt_version`.

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

Seed sources are inserted on first boot (CISA KEV, GitHub Advisories, NVD,
plus a few RSS feeds). The worker polls due sources every minute; the first
ingestion cycle runs immediately at startup.

To force a fetch of one source:

```bash
curl -X POST http://localhost:8000/api/sources/cisa-kev/fetch
```

## LLM configuration

The system talks to any OpenAI-compatible endpoint. Default targets local
Ollama on the host (`gpt-oss:20b` for reasoning, `nomic-embed-text` for
embeddings). Point `LLM_BASE_URL` at vLLM, llama.cpp's server, or a cloud
provider instead — see `.env.example`.

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
    connectors/          base + cisa_kev, github_advisories, nvd, rss, github_releases
    pipeline/            normalize, dedupe, extract, classify, score, llm, embed, ingest
    search/hybrid.py     BM25-ish FTS + pgvector, reciprocal-rank fusion
    api/                 REST routes
    worker.py            arq worker: scheduler + fetch/process tasks
    mcp_server.py        read-only MCP tools over streamable HTTP
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

## Roadmap mapping (from the design doc)

| Doc milestone | Where it lands |
|---|---|
| Weeks 2–4 source registry + raw ingestion | `app/connectors`, `sources` table, MinIO |
| Weeks 4–6 canonical schema, parsing, dedupe | `app/schemas.py`, `app/pipeline/{normalize,dedupe}.py` |
| Weeks 5–8 hybrid search | `app/search/hybrid.py` |
| Weeks 6–9 LLM extraction + summaries | `app/pipeline/llm.py`, `analyses` table |
| Weeks 8–10 relevance + alerts | `app/pipeline/score.py`, `alerts` table |
| Weeks 9–12 dashboard + watchlists | `frontend/` |
| Weeks 11–14 MCP/API | `app/mcp_server.py`, `app/api/` |
| Months 4–6 graph + trends | entity/event_entity tables seeded; graph UI TBD |

Deliberately stubbed for later: SimHash/MinHash near-dupe detection, change
significance modelling, OpenCTI/MISP export, analyst-auth RBAC, trend
clustering UI. Each has a marked extension point in the code.
