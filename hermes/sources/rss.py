from __future__ import annotations

import feedparser
import httpx

from ..models import RawOpportunity
from .base import Source

# feed url -> (category hint, region hint)
FEEDS = {
    "https://github.blog/feed/": ("dev_programs", "global"),
    "https://dev.to/feed/tag/hackathon": ("hackathons", "global"),
    "https://dev.to/feed/tag/opensource": ("dev_programs", "global"),
    "https://www.freecodecamp.org/news/rss/": ("free_courses", "global"),
    "https://huggingface.co/blog/feed.xml": ("ai_freebies", "global"),
    "https://www.producthunt.com/feed": ("beta_early_access", "global"),
}


class RSS(Source):
    name = "rss"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawOpportunity]:
        out: list[RawOpportunity] = []
        for url, (category, region) in FEEDS.items():
            r = await client.get(url)
            if r.status_code != 200:
                continue
            feed = feedparser.parse(r.text)
            for entry in feed.entries[:15]:
                title = getattr(entry, "title", "")
                link = getattr(entry, "link", "")
                if not title or not link:
                    continue
                out.append(RawOpportunity(
                    title=title,
                    url=link,
                    source=f"{self.name}/{feed.feed.get('title', url)[:40]}",
                    description=getattr(entry, "summary", "")[:500],
                    category=category,
                    region_hint=region,
                    posted_at=getattr(entry, "published", ""),
                ))
        return out
