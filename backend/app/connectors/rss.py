"""Generic RSS/Atom connector — covers vendor PSIRT feeds, security research
blogs, AI vendor blogs, mailing-list archives (SecLists) and conference news.

feedparser handles RSS 0.9x/1.0/2.0 and Atom uniformly — and never raises on
a broken feed, so a dead URL can "succeed" forever while ingesting nothing
(round-1: arXiv's legacy host returned a well-formed feed with zero items).
Fail loudly instead: a parse error or a zero-entry body is a fetch failure.
"""

import logging
from datetime import datetime, timedelta, timezone

import feedparser
from dateutil import parser as dtparser

from app.config import settings
from app.connectors.base import Connector, FetchResult, register
from app.pipeline.normalize import html_to_text
from app.schemas import CanonicalEnvelope

log = logging.getLogger(__name__)

# Page fetches for title-only feeds are bounded per poll; the rest catch up
# on later polls (only entries inside the backfill window are worth it).
MAX_PAGE_FETCHES = 25


@register
class RssConnector(Connector):
    name = "rss"

    async def fetch(self) -> FetchResult:
        resp = await self.get(self.source.url)
        if resp.status_code == 304:
            return [], {}
        feed = feedparser.parse(resp.content)

        if feed.bozo and not feed.entries:
            raise RuntimeError(f"feed parse failed for {self.source.url}: {feed.bozo_exception}")
        if not feed.entries:
            raise RuntimeError(f"feed returned 0 entries for {self.source.url}")
        if feed.bozo:
            log.warning("feed %s parsed with bozo flag: %s", self.source.url, feed.bozo_exception)

        envelopes: list[CanonicalEnvelope] = []
        for entry in feed.entries:
            # Skip content-free entries (no title and no body): they ingest
            # as undated junk rows.
            body = entry.get("summary", "")
            if entry.get("content"):
                body = entry.content[0].get("value", body)
            if not (entry.get("title", "").strip() or body.strip()):
                log.warning("skipping content-free entry in %s", self.source.url)
                continue
            external_id = entry.get("id") or entry.get("link")
            published = _first_date(entry, "published_parsed", "updated_parsed", "published", "updated")
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
        # Some feeds ship titles only (Hugging Face: 896/896 entries, verified
        # 2026-11-03). A bare title can't be classified, scored or summarised,
        # so fetch the article page for recent title-only entries.
        page_fetches = 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.backfill_max_age_days)
        for env in envelopes:
            if env.body_text.strip() or page_fetches >= MAX_PAGE_FETCHES:
                continue
            if env.published_at and env.published_at < cutoff:
                continue
            try:
                page = await self.get(env.source_url)
            except Exception as exc:
                log.warning("article page fetch failed for %s: %s", env.source_url, exc)
                continue
            env.body_text = html_to_text(page.text)[:5000]
            # The article bytes become the raw evidence — otherwise the
            # content hash still reflects the title-only feed entry and the
            # fetched body is silently discarded as "unchanged".
            env.raw_content = page.content
            env.raw_content_type = "text/html"
            page_fetches += 1
        if page_fetches:
            log.info("fetched %d article pages for title-only feed %s", page_fetches, self.source.url)

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
