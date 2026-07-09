from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from ..models import RawOpportunity

HEADERS = {"User-Agent": "Hermes/0.1 (personal opportunity tracker; contact: local user)"}

# Some retail/CDN-fronted sites reject non-browser UAs (while Reddit rejects
# browser UAs from datacenter-ish clients) — sources pick per request.
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                  " (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
}


class Source(ABC):
    """A discovery plugin. Implement fetch(); errors are isolated per-source upstream."""

    name: str = "base"

    @abstractmethod
    async def fetch(self, client: httpx.AsyncClient) -> list[RawOpportunity]: ...
