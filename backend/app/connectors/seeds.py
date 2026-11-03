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
        "url": "https://security.googleblog.com/feeds/posts/default",
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
]
