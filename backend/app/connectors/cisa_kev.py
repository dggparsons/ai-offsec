"""CISA Known Exploited Vulnerabilities catalogue.

Machine-readable JSON feed — the canonical P0 source for "known to be
exploited" status. https://www.cisa.gov/known-exploited-vulnerabilities-catalog
"""

from dateutil import parser as dtparser

from app.connectors.base import Connector, FetchResult, register
from app.schemas import CanonicalEnvelope, Identifiers

FEED_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


@register
class CisaKevConnector(Connector):
    name = "cisa_kev"

    async def fetch(self) -> FetchResult:
        resp = await self.get(FEED_URL)
        if resp.status_code == 304:
            return [], {}
        data = resp.json()
        envelopes: list[CanonicalEnvelope] = []
        for vuln in data.get("vulnerabilities", []):
            cve = vuln.get("cveID", "")
            title = f"{cve}: {vuln.get('vulnerabilityName', '')}"
            body = (
                f"Vendor: {vuln.get('vendorProject', '')}\n"
                f"Product: {vuln.get('product', '')}\n"
                f"Description: {vuln.get('shortDescription', '')}\n"
                f"Required action: {vuln.get('requiredAction', '')}\n"
                f"Due date: {vuln.get('dueDate', '')}\n"
                f"Known ransomware campaign use: {vuln.get('knownRansomwareCampaignUse', 'Unknown')}\n"
                f"Notes: {vuln.get('notes', '')}"
            )
            envelopes.append(
                CanonicalEnvelope(
                    source_id=self.source.slug,
                    source_url=f"https://www.cisa.gov/known-exploited-vulnerabilities-catalog?search_api_fulltext={cve}",
                    source_type="exploited_vulnerability",
                    external_id=cve,
                    published_at=_date(vuln.get("dateAdded")),
                    modified_at=_date(vuln.get("dateAdded")),
                    title=title,
                    body_text=body,
                    raw_content=body.encode(),
                    raw_content_type="application/json",
                    identifiers=Identifiers(cve=[cve] if cve else []),
                    taxonomy=["offsec.vulnerability"],
                    source_confidence=1.0,
                    tlp="CLEAR",
                )
            )
        return envelopes, self.validators(resp)


def _date(value: str | None):
    if not value:
        return None
    try:
        return dtparser.parse(value)
    except (ValueError, OverflowError):
        return None
