"""Devpost — open hackathons with real prizes and deadlines (public JSON API)."""

from __future__ import annotations

import httpx

from ..models import RawOpportunity
from .base import BROWSER_HEADERS, Source

API = "https://devpost.com/api/hackathons"


class Devpost(Source):
    name = "devpost"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawOpportunity]:
        out: list[RawOpportunity] = []
        for page in (1, 2):
            r = await client.get(
                API, params={"status[]": "open", "page": page}, headers=BROWSER_HEADERS
            )
            if r.status_code != 200:
                break
            for h in r.json().get("hackathons", []):
                title = h.get("title") or ""
                url = h.get("url") or ""
                if not title or not url:
                    continue
                bits = []
                if h.get("prize_amount"):
                    bits.append(f"Prizes: {h['prize_amount']}")
                if h.get("submission_period_dates"):
                    bits.append(f"Submit: {h['submission_period_dates']}")
                loc = (h.get("displayed_location") or {}).get("location", "")
                if loc:
                    bits.append(loc)
                themes = ", ".join(t.get("name", "") for t in h.get("themes", [])[:4])
                if themes:
                    bits.append(themes)
                out.append(RawOpportunity(
                    title=title,
                    url=url,
                    source=self.name,
                    description=" · ".join(bits),
                    category="hackathons",
                    category_pinned=True,
                ))
        return out
