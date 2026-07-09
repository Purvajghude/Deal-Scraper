"""dealsheaven.in — Indian deal aggregator (shopping, food, bank offers).

Plain server-rendered HTML; deal cards are anchors to /deal/<slug>. Food deals
are routed to food_dining by the keyword categorizer (category not pinned).
"""

from __future__ import annotations

import re

import httpx

from ..models import RawOpportunity
from .base import BROWSER_HEADERS, Source

PAGES = [
    "https://dealsheaven.in/",
    "https://dealsheaven.in/category/freebies-freesamples",
]
DEAL_ANCHOR = re.compile(r'<a[^>]+href="(/deal/[^"]+)"[^>]*>([^<]{10,})</a>')


class DealsHeaven(Source):
    name = "dealsheaven.in"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawOpportunity]:
        out: list[RawOpportunity] = []
        seen: set[str] = set()
        for page in PAGES:
            r = await client.get(page, headers=BROWSER_HEADERS)
            if r.status_code != 200:
                continue
            for path, title in DEAL_ANCHOR.findall(r.text):
                title = re.sub(r"\s+", " ", title).replace("&amp;", "&").strip()
                if path in seen or not title:
                    continue
                seen.add(path)
                out.append(RawOpportunity(
                    title=title,
                    url="https://dealsheaven.in" + path,
                    source=self.name,
                    category="deals_shopping",
                    region_hint="india",
                ))
        return out
