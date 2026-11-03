"""Seed source registry — the P0/P1 set from the design doc.

Inserted on startup when the sources table is empty. Extend in the dashboard
or via the API; the registry row (not code) is the operational source of
truth for polling cadence, trust score and licence policy.
"""

SEED_SOURCES: list[dict] = [
    # --- P0: exploited vulnerabilities ---
    {
        "slug": "cisa-kev",
        "name": "CISA Known Exploited Vulnerabilities",
        "connector": "cisa_kev",
        "url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
        "source_type": "exploited_vulnerability",
        "priority": "P0",
        "poll_interval_sec": 900,
        "trust_score": 1.0,
    },
    {
        "slug": "github-advisories",
        "name": "GitHub Security Advisory Database",
        "connector": "github_advisories",
        "url": "https://github.com/advisories",
        "source_type": "security_advisory",
        "priority": "P0",
        "poll_interval_sec": 900,
        "trust_score": 0.95,
    },
    {
        "slug": "nvd-cves",
        "name": "NVD CVE Feed",
        "connector": "nvd",
        "url": "https://nvd.nist.gov/",
        "source_type": "vulnerability_record",
        "priority": "P0",
        "poll_interval_sec": 1800,
        "trust_score": 1.0,
    },
    # --- P0: local inference engines ---
    {
        "slug": "inference-engines",
        "name": "Local inference engines (llama.cpp / vLLM / Ollama)",
        "connector": "github_releases",
        "url": "https://github.com",
        "source_type": "repository_release",
        "priority": "P0",
        "poll_interval_sec": 900,
        "trust_score": 0.9,
        "config": {"repos": ["ggml-org/llama.cpp", "vllm-project/vllm", "ollama/ollama"]},
    },
    # --- P0/P1: MCP ecosystem ---
    {
        "slug": "mcp-spec",
        "name": "Model Context Protocol specification",
        "connector": "github_releases",
        "url": "https://modelcontextprotocol.io",
        "source_type": "specification",
        "priority": "P0",
        "poll_interval_sec": 3600,
        "trust_score": 0.95,
        "config": {"repos": ["modelcontextprotocol/modelcontextprotocol", "modelcontextprotocol/servers"]},
    },
    # --- P1: AI-security frameworks & research ---
    {
        "slug": "google-security-blog",
        "name": "Google Security Blog",
        "connector": "rss",
        # Moved from security.googleblog.com (301s to blog.google; old
        # Feedburner feed stopped updating April 2026 — verified 2026-11-03).
        "url": "https://blog.google/security/rss/",
        "source_type": "security_research",
        "priority": "P1",
        "poll_interval_sec": 3600,
        "trust_score": 0.9,
    },
    {
        "slug": "trailofbits-blog",
        "name": "Trail of Bits Blog",
        "connector": "rss",
        "url": "https://blog.trailofbits.com/feed/",
        "source_type": "security_research",
        "priority": "P1",
        "poll_interval_sec": 3600,
        "trust_score": 0.9,
    },
    {
        "slug": "seclists-fulldisclosure",
        "name": "Full Disclosure (SecLists)",
        "connector": "rss",
        "url": "https://seclists.org/rss/fulldisclosure.rss",
        "source_type": "mailing_list",
        "priority": "P0",
        "poll_interval_sec": 1800,
        "trust_score": 0.7,
    },
    # --- P2: discovery only, never authoritative ---
    {
        "slug": "hn-frontpage",
        "name": "Hacker News (front page)",
        "connector": "rss",
        "url": "https://hnrss.org/frontpage",
        "source_type": "forum_discovery",
        "priority": "P2",
        "poll_interval_sec": 1800,
        "trust_score": 0.3,
    },
    # --- P1: AI vendors & research ---
    {
        "slug": "huggingface-blog",
        "name": "Hugging Face Blog",
        "connector": "rss",
        "url": "https://huggingface.co/blog/feed.xml",
        "source_type": "vendor_blog",
        "priority": "P1",
        "poll_interval_sec": 3600,
        "trust_score": 0.9,
    },
    {
        "slug": "openai-news",
        "name": "OpenAI News",
        "connector": "rss",
        "url": "https://openai.com/news/rss.xml",
        "source_type": "vendor_blog",
        "priority": "P1",
        "poll_interval_sec": 3600,
        "trust_score": 0.95,
    },
    {
        "slug": "arxiv-cscr",
        "name": "arXiv cs.CR (Cryptography & Security)",
        "connector": "rss",
        # Canonical host per arXiv docs (info.arxiv.org/help/rss.html). The
        # legacy export.arxiv.org host returns a well-formed feed with ZERO
        # items — fetches "succeeded" while ingesting nothing (round-1).
        "url": "https://rss.arxiv.org/rss/cs.CR",
        "source_type": "research",
        "priority": "P1",
        "poll_interval_sec": 14400,
        "trust_score": 0.8,
    },
    # --- P1: AI coverage gaps (verified live 2026-11-03) ---
    {
        "slug": "simon-willison",
        "name": "Simon Willison's Weblog",
        "connector": "rss",
        # Fastest independent model-release + prompt-injection coverage.
        "url": "https://simonwillison.net/atom/everything/",
        "source_type": "security_research",
        "priority": "P1",
        "poll_interval_sec": 3600,
        "trust_score": 0.85,
    },
    {
        "slug": "embrace-the-red",
        "name": "Embrace The Red",
        "connector": "rss",
        # Prompt-injection / agent-security research — the closest thing to a
        # dedicated AI-pentest-methodology feed.
        "url": "https://embracethered.com/blog/index.xml",
        "source_type": "security_research",
        "priority": "P1",
        "poll_interval_sec": 3600,
        "trust_score": 0.85,
    },
    {
        "slug": "deepmind-blog",
        "name": "Google DeepMind Blog",
        "connector": "rss",
        "url": "https://deepmind.google/blog/rss.xml",
        "source_type": "vendor_blog",
        "priority": "P1",
        "poll_interval_sec": 3600,
        "trust_score": 0.9,
    },
    {
        "slug": "google-ai-blog",
        "name": "Google AI Blog",
        "connector": "rss",
        "url": "https://blog.google/technology/ai/rss/",
        "source_type": "vendor_blog",
        "priority": "P1",
        "poll_interval_sec": 3600,
        "trust_score": 0.9,
    },
    # Note: Anthropic publishes no public RSS (verified 2026-11) — needs an
    # HTML connector when one is written; Simon Willison covers their
    # releases independently in the meantime.
]
