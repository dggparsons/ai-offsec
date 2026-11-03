"""Generic RSS/Atom connector — covers vendor PSIRT feeds, security research
blogs, AI vendor blogs, mailing-list archives (SecLists) and conference news.

feedparser handles RSS 0.9x/1.0/2.0 and Atom uniformly.
"""

import feedparser
from dateutil import parser as dtparser

from app.connectors.base import Connector, FetchResult, register
from app.schemas import CanonicalEnvelope


@register
class RssConnector(Connector):
    name = "rss"

    async def fetch(self) -> FetchResult:
        resp = await self.get(self.source.url)
        if resp.status_code == 304:
            return [], {}
        feed = feedparser.parse(resp.content)

        envelopes: list[CanonicalEnvelope] = []
        for entry in feed.entries:
            external_id = entry.get("id") or entry.get("link")
            published = _first_date(entry, "published_parsed", "updated_parsed", "published", "updated")
            body = entry.get("summary", "")
            if entry.get("content"):
                body = entry.content[0].get("value", body)
            author = entry.get("author", "")
            envelopes.append(
                CanonicalEnvelope(
                    source_id=self.source.slug,
                    source_url=entry.get("link", self.source.url),
                    source_type=self.source.source_type,
                    external_id=external_id,
                    published_at=published,
                    modified_at=published,
                    title=entry.get("title", ""),
                    body_text=body,
                    author=author,
                    raw_content=(entry.get("title", "") + "\n\n" + body).encode(),
                    raw_content_type="application/rss+xml",
                    source_confidence=self.source.trust_score,
                    tlp=self.source.tlp,
                    licence=self.source.licence,
                )
            )
        return envelopes, self.validators(resp)


def _first_date(entry, *keys):
    for key in keys:
        value = entry.get(key)
        if value is None:
            continue
        if hasattr(value, "tm_year"):  # time.struct_time
            import calendar
            from datetime import datetime, timezone

            return datetime.fromtimestamp(calendar.timegm(value), tz=timezone.utc)
        try:
            return dtparser.parse(str(value))
        except (ValueError, OverflowError):
            continue
    return None
