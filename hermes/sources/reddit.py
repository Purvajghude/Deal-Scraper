from __future__ import annotations

import asyncio

import feedparser
import httpx

from ..models import RawOpportunity
from .base import Source

# Reddit's JSON API 403s anonymous non-OAuth clients aggressively, but the
# public RSS endpoints answer 200 to a plain identifying UA. Same content.
# subreddit -> (category hint, region hint, required keywords or None)
# Discussion-heavy subs get a keyword gate so career talk doesn't reach the
# register; dedicated freebie subs pass everything.
OPPORTUNITY_WORDS = (
    "free", "offer", "discount", "credit", "deal", "giveaway", "coupon",
    "scholarship", "internship", "fellowship", "hackathon", "program",
    "beta", "voucher", "launch", "released", "release", "open weights",
    "api", "trial", "student",
)

SUBREDDITS: dict[str, tuple[str, str, tuple[str, ...] | None]] = {
    "developersIndia": ("dev_programs", "india", OPPORTUNITY_WORDS),
    "udemyfreebies": ("free_courses", "global", None),
    "hackathon": ("hackathons", "global", None),
    "LocalLLaMA": ("ai_freebies", "global", OPPORTUNITY_WORDS),
    "FREE": ("deals_shopping", "global", None),
    "eFreebies": ("deals_shopping", "global", None),
    "dealsforindia": ("deals_shopping", "india", None),
    # r/scholarships was tried and dropped: US college-application discussion,
    # not claimable Indian scholarships. PIB covers govt schemes; a proper
    # Indian scholarship source (NSP/Buddy4Study) has no public feed yet.
}


class Reddit(Source):
    name = "reddit"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawOpportunity]:
        out: list[RawOpportunity] = []
        for i, (sub, (category, region, required)) in enumerate(SUBREDDITS.items()):
            if i:
                await asyncio.sleep(8)  # anonymous quota is tiny; pace generously
            url = f"https://www.reddit.com/r/{sub}/hot.rss"
            r = await client.get(url, params={"limit": 25})
            if r.status_code == 429:
                await asyncio.sleep(35)
                r = await client.get(url, params={"limit": 25})
            if r.status_code != 200:  # quota exhausted; the next 6-hourly refresh catches up
                continue
            feed = feedparser.parse(r.text)
            for entry in feed.entries:
                title = getattr(entry, "title", "")
                link = getattr(entry, "link", "")
                if not title or not link:
                    continue
                if required and not any(w in title.lower() for w in required):
                    continue
                out.append(RawOpportunity(
                    title=title,
                    url=link,
                    source=f"{self.name}/{sub}",
                    description="",
                    category=category,
                    region_hint=region,
                    posted_at=getattr(entry, "published", ""),
                ))
        return out
