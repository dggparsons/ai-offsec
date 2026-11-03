"""NVD CVE API 2.0 — structured vulnerability metadata.

https://nvd.nist.gov/developers/vulnerabilities
Polled incrementally with lastModStartDate/lastModEndDate windows.
"""

import json
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.connectors.base import Connector, FetchResult, register
from app.schemas import CanonicalEnvelope, Identifiers

API = "https://services.nvd.nist.gov/rest/json/cves/2.0"


@register
class NvdConnector(Connector):
    name = "nvd"

    def headers(self) -> dict[str, str]:
        h = super().headers()
        if settings.nvd_api_key:
            h["apiKey"] = settings.nvd_api_key
        return h

    async def fetch(self) -> FetchResult:
        now = datetime.now(timezone.utc)
        # Cursor: resume from last success, else look back one day. NVD
        # rejects windows > 120 days, so clamp.
        cursor_raw = self.source.config.get("modified_cursor")
        try:
            start = datetime.fromisoformat(cursor_raw) if cursor_raw else now - timedelta(days=1)
        except ValueError:
            start = now - timedelta(days=1)
        if start < now - timedelta(days=119):
            start = now - timedelta(days=119)

        # Page through the window (round-1 fix: a single page silently dropped
        # everything past the first 100 modified CVEs). Bounded per poll; if
        # more remain, the cursor only advances to the last item seen, so the
        # next poll resumes rather than skipping.
        page_size = 100
        max_pages = 5
        vulnerabilities: list[dict] = []
        total_results = 0
        last_modified_seen: str | None = None
        for page in range(max_pages):
            params = {
                "lastModStartDate": start.strftime("%Y-%m-%dT%H:%M:%S.000"),
                "lastModEndDate": now.strftime("%Y-%m-%dT%H:%M:%S.000"),
                "resultsPerPage": str(page_size),
                "startIndex": str(page * page_size),
            }
            resp = await self.get(API, params=params)
            if resp.status_code == 304:
                break
            data = resp.json()
            total_results = data.get("totalResults", 0)
            batch = data.get("vulnerabilities", [])
            vulnerabilities.extend(batch)
            if batch:
                last_modified_seen = batch[-1].get("cve", {}).get("lastModified") or last_modified_seen
            if (page + 1) * page_size >= total_results:
                break
            # NVD rate limit: 5 requests / 30 s without an API key.
            if not settings.nvd_api_key:
                import asyncio

                await asyncio.sleep(7)

        envelopes: list[CanonicalEnvelope] = []
        for item in vulnerabilities:
            cve = item.get("cve", {})
            cve_id = cve.get("id", "")
            desc = next(
                (d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"), ""
            )
            weaknesses = [
                d["value"]
                for w in cve.get("weaknesses", [])
                for d in w.get("description", [])
                if d.get("value", "").startswith("CWE-")
            ]
            metrics = cve.get("metrics", {})
            cvss = ""
            for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                if metrics.get(key):
                    m = metrics[key][0].get("cvssData", {})
                    cvss = f"CVSS {m.get('version')}: {m.get('baseScore')} ({m.get('baseSeverity', m.get('severity', ''))})"
                    break
            body = f"{desc}\n\n{cvss}\nWeaknesses: {', '.join(weaknesses)}"
            envelopes.append(
                CanonicalEnvelope(
                    source_id=self.source.slug,
                    source_url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                    source_type="vulnerability_record",
                    external_id=cve_id or None,
                    published_at=_dt(cve.get("published")),
                    modified_at=_dt(cve.get("lastModified")),
                    title=f"{cve_id}: {desc[:120]}",
                    body_text=body,
                    # Per-item bytes: the page response belongs to the last
                    # page fetched, not to every item in the window.
                    raw_content=json.dumps(item).encode(),
                    raw_content_type="application/json",
                    identifiers=Identifiers(cve=[cve_id] if cve_id else [], cwe=weaknesses),
                    taxonomy=["offsec.vulnerability"],
                    source_confidence=1.0,
                    tlp="CLEAR",
                )
            )
        # Advance the cursor to `now` only when the whole window was paged;
        # if the page cap cut the window short, resume from the last item
        # actually seen so the tail is picked up next poll.
        covered = len(vulnerabilities) >= total_results
        cursor = now.isoformat() if covered else (last_modified_seen or start.isoformat())
        self.source.config = {**self.source.config, "modified_cursor": cursor}
        return envelopes, {}


def _dt(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
