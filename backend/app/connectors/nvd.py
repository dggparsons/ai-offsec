"""NVD CVE API 2.0 — structured vulnerability metadata.

https://nvd.nist.gov/developers/vulnerabilities
Polled incrementally with lastModStartDate/lastModEndDate windows.
"""

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

        params = {
            "lastModStartDate": start.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "lastModEndDate": now.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "resultsPerPage": "100",
        }
        resp = await self.get(API, params=params)
        if resp.status_code == 304:
            return [], {}
        data = resp.json()

        envelopes: list[CanonicalEnvelope] = []
        for item in data.get("vulnerabilities", []):
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
                    raw_content=resp.content,
                    raw_content_type="application/json",
                    identifiers=Identifiers(cve=[cve_id] if cve_id else [], cwe=weaknesses),
                    taxonomy=["offsec.vulnerability"],
                    source_confidence=1.0,
                    tlp="CLEAR",
                )
            )
        self.source.config = {**self.source.config, "modified_cursor": now.isoformat()}
        return envelopes, {}


def _dt(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
