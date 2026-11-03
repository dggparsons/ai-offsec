"""GitHub releases connector for watched repositories.

Tracks inference engines (llama.cpp, vLLM, Ollama), MCP spec/servers and
other P0 projects. Configure via source config: {"repos": ["ggml-org/llama.cpp", ...]}.
Uses per-repo ETags through the base class's conditional-request support.
"""

import logging

from dateutil import parser as dtparser

from app.config import settings
from app.connectors.base import Connector, FetchResult, register
from app.schemas import CanonicalEnvelope, Identifiers

log = logging.getLogger(__name__)

API = "https://api.github.com/repos/{repo}/releases"


@register
class GithubReleasesConnector(Connector):
    name = "github_releases"

    def headers(self) -> dict[str, str]:
        h = super().headers()
        h["Accept"] = "application/vnd.github+json"
        h["X-GitHub-Api-Version"] = "2026-03-10"
        if settings.github_token:
            h["Authorization"] = f"Bearer {settings.github_token}"
        return h

    async def fetch(self) -> FetchResult:
        repos: list[str] = self.source.config.get("repos", [])
        seen_tags: dict[str, str] = self.source.config.get("seen_tags", {})
        envelopes: list[CanonicalEnvelope] = []
        failed = 0

        for repo in repos:
            try:
                resp = await self.get(API.format(repo=repo), params={"per_page": "5"})
            except Exception as exc:
                log.warning("release fetch failed for %s: %s", repo, exc)
                failed += 1
                continue
            if resp.status_code == 304:
                continue
            for rel in resp.json():
                tag = rel.get("tag_name", "")
                if not tag or seen_tags.get(repo) == tag:
                    continue
                envelopes.append(
                    CanonicalEnvelope(
                        source_id=self.source.slug,
                        source_url=rel.get("html_url", ""),
                        source_type=self.source.source_type or "repository_release",
                        external_id=f"{repo}@{rel.get('id', tag)}",
                        published_at=_dt(rel.get("published_at")),
                        title=_title(repo, tag, rel.get("name", "")),
                        body_text=rel.get("body", "") or "",
                        author=(rel.get("author") or {}).get("login", ""),
                        raw_content=(rel.get("body", "") or "").encode(),
                        raw_content_type="application/json",
                        identifiers=Identifiers(repository=[repo]),
                        taxonomy=self._taxonomy(),
                        source_confidence=0.9,
                        tlp="CLEAR",
                    )
                )
                seen_tags[repo] = tag
        if failed == len(repos) and repos:
            raise RuntimeError(f"all {failed} watched repos failed to fetch")
        self.source.config = {**self.source.config, "seen_tags": seen_tags}
        return envelopes, {}

    def _taxonomy(self) -> list[str]:
        """The registry row, not this connector, decides what the releases
        are about (round-1 fix: MCP spec releases were labelled ai.inference)."""
        configured = self.source.config.get("taxonomy")
        if configured:
            return list(configured)
        if self.source.source_type == "specification":
            return ["mcp.specification"]
        return ["ai.inference"]


def _title(repo: str, tag: str, name: str) -> str:
    """Human headline, never 'repo b12077: b12077'."""
    project = repo.split("/")[-1]
    name = (name or "").strip()
    if not name or name == tag:
        return f"{project} release {tag}"
    return f"{project} {tag}: {name}"


def _dt(value: str | None):
    if not value:
        return None
    try:
        return dtparser.parse(value)
    except (ValueError, OverflowError):
        return None
