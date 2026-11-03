"""GitHub releases connector for watched repositories.

Tracks inference engines (llama.cpp, vLLM, Ollama), MCP spec/servers and
other P0 projects. Configure via source config: {"repos": ["ggml-org/llama.cpp", ...]}.
Uses per-repo ETags through the base class's conditional-request support.
"""

from dateutil import parser as dtparser

from app.config import settings
from app.connectors.base import Connector, FetchResult, register
from app.schemas import CanonicalEnvelope, Identifiers

API = "https://api.github.com/repos/{repo}/releases"


@register
class GithubReleasesConnector(Connector):
    name = "github_releases"

    def headers(self) -> dict[str, str]:
        h = super().headers()
        h["Accept"] = "application/vnd.github+json"
        h["X-GitHub-Api-Version"] = "2022-11-28"
        if settings.github_token:
            h["Authorization"] = f"Bearer {settings.github_token}"
        return h

    async def fetch(self) -> FetchResult:
        repos: list[str] = self.source.config.get("repos", [])
        seen_tags: dict[str, str] = self.source.config.get("seen_tags", {})
        envelopes: list[CanonicalEnvelope] = []

        for repo in repos:
            try:
                resp = await self.get(API.format(repo=repo), params={"per_page": "5"})
            except Exception:
                continue  # logged upstream by retry layer; keep other repos flowing
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
                        source_type="repository_release",
                        external_id=f"{repo}@{rel.get('id', tag)}",
                        published_at=_dt(rel.get("published_at")),
                        title=f"{repo} {tag}: {rel.get('name', '')}",
                        body_text=rel.get("body", "") or "",
                        author=(rel.get("author") or {}).get("login", ""),
                        raw_content=(rel.get("body", "") or "").encode(),
                        raw_content_type="application/json",
                        identifiers=Identifiers(repository=[repo]),
                        taxonomy=["ai.inference"],
                        source_confidence=0.9,
                        tlp="CLEAR",
                    )
                )
                seen_tags[repo] = tag
        self.source.config = {**self.source.config, "seen_tags": seen_tags}
        return envelopes, {}


def _dt(value: str | None):
    if not value:
        return None
    try:
        return dtparser.parse(value)
    except (ValueError, OverflowError):
        return None
