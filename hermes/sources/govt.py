"""Government of India — PIB (Press Information Bureau) press releases.

PIB publishes an all-ministries RSS feed. Most entries are routine press
notes, so we keep only items that smell like a scheme, benefit, scholarship,
or launch a citizen can actually claim.
"""

from __future__ import annotations

import feedparser
import httpx

from ..models import RawOpportunity
from .base import BROWSER_HEADERS, Source

FEED = "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"

# The PIB feed serves Hindi titles regardless of the Lang param, so the filter
# carries both Hindi and English scheme vocabulary.
SCHEME_KEYWORDS = (
    # English
    "yojana", "yojna", "scheme", "scholarship", "fellowship", "stipend",
    "subsidy", "free ", "benefit", "portal", "launch", "students", "farmers",
    "women", "startup", "skill", "loan", "insurance", "pension", "grant",
    "registration open", "applications", "apply",
    # Hindi
    "योजना", "छात्रवृत्ति", "मुफ्त", "निःशुल्क", "नि:शुल्क", "लाभ", "सब्सिडी",
    "पोर्टल", "शुभारंभ", "शुरू", "लॉन्च", "छात्र", "विद्यार्थि", "किसान",
    "महिला", "स्टार्टअप", "कौशल", "ऋण", "बीमा", "पेंशन", "अनुदान", "आवेदन",
    "पंजीकरण", "वजीफा",
)


class GovtSchemes(Source):
    name = "pib.gov.in"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawOpportunity]:
        r = await client.get(FEED, headers=BROWSER_HEADERS)
        r.raise_for_status()
        feed = feedparser.parse(r.text)
        out: list[RawOpportunity] = []
        for entry in feed.entries:
            title = getattr(entry, "title", "")
            link = getattr(entry, "link", "")
            summary = getattr(entry, "summary", "")[:500]
            text = f"{title} {summary}".lower()
            if not title or not link:
                continue
            if not any(k in text for k in SCHEME_KEYWORDS):
                continue
            out.append(RawOpportunity(
                title=title,
                url=link,
                source=self.name,
                description=summary,
                category="govt_schemes",
                category_pinned=True,
                region_hint="india",
                posted_at=getattr(entry, "published", ""),
            ))
        return out
