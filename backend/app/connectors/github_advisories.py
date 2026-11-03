"""GitHub global security advisories (GHSA) via the REST API.

https://docs.github.com/en/rest/security-advisories/global-advisories
Reviewed advisories across open-source ecosystems — a P0 machine-readable
source. Uses `modified` cursor pagination stored in source.config.
"""

import json

from dateutil import parser as dtparser

from app.config import settings
from app.connectors.base import Connector, FetchResult, register
from app.schemas import CanonicalEnvelope, Identifiers

API = "https://api.github.com/advisories"


@register
class GithubAdvisoriesConnector(Connector):
    name = "github_advisories"

    def headers(self) -> dict[str, str]:
        h = super().headers()
        h["Accept"] = "application/vnd.github+json"
        h["X-GitHub-Api-Version"] = "2026-03-10"
        if settings.github_token:
            h["Authorization"] = f"Bearer {settings.github_token}"
        return h

    async def fetch(self) -> FetchResult:
        # Paginate with the documented Link-header cursors, oldest first, so
        # a burst of >per_page modified advisories is never skipped over
        # (round-1 fix: the cursor used to jump past anything beyond page 1).
        params: dict[str, str] = {"per_page": "100", "sort": "updated", "direction": "asc"}
        if cursor := self.source.config.get("modified_cursor"):
            params["modified"] = f">{cursor}"

        advisories: list[dict] = []
        url, page_params = API, params
        for _page in range(5):  # bounded: 500 advisories per poll is plenty
            resp = await self.get(url, params=page_params)
            if resp.status_code == 304:
                break
            advisories.extend(resp.json())
            nxt = resp.links.get("next")
            if not nxt:
                break
            url, page_params = nxt["url"], None  # the next URL carries its own params

        envelopes: list[CanonicalEnvelope] = []
        newest_modified: str | None = None
        for adv in advisories:
            ghsa = adv.get("ghsa_id", "")
            cves = [adv["cve_id"]] if adv.get("cve_id") else []
            cwes = [c["cwe_id"] for c in adv.get("cwes", []) if c.get("cwe_id")]
            published = _dt(adv.get("published_at"))
            modified = _dt(adv.get("updated_at"))
            if modified and (newest_modified is None or modified.isoformat() > newest_modified):
                newest_modified = modified.isoformat()
            envelopes.append(
                CanonicalEnvelope(
                    source_id=self.source.slug,
                    source_url=adv.get("html_url", ""),
                    source_type="security_advisory",
                    external_id=ghsa or None,
                    published_at=published,
                    modified_at=modified,
                    title=adv.get("summary", ghsa),
                    body_text=adv.get("description", ""),
                    author=(adv.get("publisher") or {}).get("login", ""),
                    # Per-item bytes: the page response is whichever page was
                    # fetched last, not evidence for this advisory.
                    raw_content=json.dumps(adv).encode(),
                    raw_content_type="application/json",
                    identifiers=Identifiers(cve=cves, ghsa=[ghsa] if ghsa else [], cwe=cwes),
                    taxonomy=["offsec.vulnerability"],
                    source_confidence=0.95,
                    tlp="CLEAR",
                )
            )
        # Persist the high-water mark so the next poll is incremental.
        if newest_modified:
            self.source.config = {**self.source.config, "modified_cursor": newest_modified}
        return envelopes, {}


def _dt(value: str | None):
    if not value:
        return None
    try:
        return dtparser.parse(value)
    except (ValueError, OverflowError):
        return None
