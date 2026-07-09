from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ..models import RawOpportunity
from .base import Source

# The Algolia HN API only allows numericFilters on created_at_i; the points
# threshold has to be applied client-side.
API = "https://hn.algolia.com/api/v1/search"
MIN_POINTS = 5

# Each query targets a distinct opportunity shape on HN.
QUERIES = [
    ("free credits", "dev_programs"),
    ("free api", "ai_freebies"),
    ("open weights model", "ai_freebies"),
    ("student program", "student_offers"),
    ("hackathon", "hackathons"),
    ("early access", "beta_early_access"),
    ("free tier", "dev_programs"),
]


class HackerNews(Source):
    name = "hackernews"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawOpportunity]:
        month_ago = int(datetime.now(timezone.utc).timestamp()) - 30 * 86400
        out: list[RawOpportunity] = []
        for query, category in QUERIES:
            r = await client.get(
                API,
                params={"query": query, "tags": "story", "hitsPerPage": 25,
                        "numericFilters": f"created_at_i>{month_ago}"},
            )
            r.raise_for_status()
            for hit in r.json().get("hits", []):
                if (hit.get("points") or 0) < MIN_POINTS:
                    continue
                title = hit.get("title") or ""
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
                if not title:
                    continue
                posted = ""
                if hit.get("created_at_i"):
                    posted = datetime.fromtimestamp(
                        hit["created_at_i"], tz=timezone.utc
                    ).isoformat(timespec="seconds")
                out.append(RawOpportunity(
                    title=title,
                    url=url,
                    source=self.name,
                    description=(hit.get("story_text") or "")[:500],
                    category=category,
                    posted_at=posted,
                ))
        return out
