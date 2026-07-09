"""studentoffers.co — verified student discount directory.

The site publishes an LLM-friendly catalog at /llms.txt: a markdown list of
every offer as `- [Name](https://.../offer/slug.md): one-line description`.
We parse that instead of scraping HTML.
"""

from __future__ import annotations

import re

import httpx

from ..models import RawOpportunity
from .base import BROWSER_HEADERS, Source

URL = "https://studentoffers.co/llms.txt"
OFFER_LINE = re.compile(r"^- \[([^\]]+)\]\((https?://[^)]+?)(?:\.md)?\): (.+)$")


class StudentOffers(Source):
    name = "studentoffers.co"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawOpportunity]:
        r = await client.get(URL, headers=BROWSER_HEADERS)
        r.raise_for_status()
        out: list[RawOpportunity] = []
        in_offers = False
        for line in r.text.splitlines():
            if line.startswith("## "):
                in_offers = line.strip() == "## Offers"
                continue
            if not in_offers:
                continue
            m = OFFER_LINE.match(line.strip())
            if not m:
                continue
            name, url, desc = m.groups()
            out.append(RawOpportunity(
                title=f"{name} — {desc}",
                url=url,
                source=self.name,
                description=desc,
                category="student_offers",
                category_pinned=True,
            ))
        return out
