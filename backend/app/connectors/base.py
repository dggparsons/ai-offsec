"""Connector framework.

A connector turns one remote source into CanonicalEnvelopes. Rules of the
road (per the design doc): prefer APIs > RSS > structured documents > HTML >
browser automation; always support conditional requests, back-off and
per-source quotas; treat everything fetched as hostile, unvalidated input.
"""

import logging
from typing import Any, Callable, Coroutine

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.models import Source
from app.schemas import CanonicalEnvelope

log = logging.getLogger(__name__)

FetchResult = tuple[list[CanonicalEnvelope], dict[str, str]]
#                                                        ^ new validator headers: {"etag": ..., "last_modified": ...}


class Connector:
    """Base class. Subclasses implement `fetch`."""

    name = "base"

    def __init__(self, source: Source):
        self.source = source

    def headers(self) -> dict[str, str]:
        headers = {"User-Agent": "ai-news-intel/0.1 (+internal research collector)"}
        if self.source.etag:
            headers["If-None-Match"] = self.source.etag
        if self.source.last_modified_header:
            headers["If-Modified-Since"] = self.source.last_modified_header
        return headers

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=60))
    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
            resp = await client.get(url, headers=self.headers(), **kwargs)
            if resp.status_code == 304:
                return resp
            resp.raise_for_status()
            return resp

    async def fetch(self) -> FetchResult:
        raise NotImplementedError

    @staticmethod
    def validators(resp: httpx.Response) -> dict[str, str]:
        out: dict[str, str] = {}
        if etag := resp.headers.get("ETag"):
            out["etag"] = etag
        if lm := resp.headers.get("Last-Modified"):
            out["last_modified"] = lm
        return out


_REGISTRY: dict[str, type[Connector]] = {}


def register(cls: type[Connector]) -> type[Connector]:
    _REGISTRY[cls.name] = cls
    return cls


def build_connector(source: Source) -> Connector:
    # Imported lazily so all connectors self-register.
    from app.connectors import cisa_kev, github_advisories, github_releases, nvd, rss  # noqa: F401

    try:
        return _REGISTRY[source.connector](source)
    except KeyError:
        raise ValueError(f"unknown connector {source.connector!r} for source {source.slug}") from None
