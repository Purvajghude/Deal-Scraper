"""Public deal feeds and optional search-index discovery, with source attribution.

Search results are leads, not checkout-verified coupons. Never invent codes.
"""
from __future__ import annotations

import asyncio
import html
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

import feedparser
import httpx

from ..config import load_profile
from ..models import RawOpportunity
from .base import Source

DEFAULT_FEEDS = [
    {"name": "Slickdeals", "url": "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1", "region": "us"},
    {"name": "OzBargain", "url": "https://www.ozbargain.com.au/deals/feed", "region": "australia"},
    {"name": "Reddit coupons", "url": "https://www.reddit.com/r/coupons/new/.rss", "region": "global"},
    {"name": "Reddit freebies", "url": "https://www.reddit.com/r/freebies/new/.rss", "region": "global"},
]
DEFAULT_QUERIES = [
    "India coupon promo code shopping", "India food delivery coupon code",
    "software developer coupon promo code", "student discount coupon",
    "cloud AI credits free offer", "shopping coupon promo code",
]


def clean(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", text)).strip()


def public_link(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        return parsed.scheme in ("http", "https") and bool(parsed.hostname) and not parsed.username
    except ValueError:
        return False


class CouponFeed(Source):
    def __init__(self, spec: dict):
        self.name = "coupons/" + spec["name"]
        self.url = spec["url"]
        self.region = spec.get("region", "global")

    async def fetch(self, client: httpx.AsyncClient) -> list[RawOpportunity]:
        response = await client.get(self.url)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if not feed.entries:
            raise ValueError("Feed returned no entries; it may be empty, blocked, or changed")
        out = []
        for entry in feed.entries[:100]:
            title, link = clean(entry.get("title", "")), entry.get("link", "")
            if not title or not public_link(link):
                continue
            timestamp = entry.get("published_parsed") or entry.get("updated_parsed")
            posted = datetime(*timestamp[:6], tzinfo=timezone.utc).isoformat() if timestamp else ""
            out.append(RawOpportunity(
                title=title, url=link, source=self.name,
                description=clean(entry.get("summary", ""))[:2000],
                category="deals_shopping", region_hint=self.region, posted_at=posted,
            ))
        return out


class CouponSearch(Source):
    name = "coupon_web_search"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawOpportunity]:
        key = os.getenv("BRAVE_SEARCH_API_KEY", "")
        if not key:
            return []
        settings = load_profile().get("discovery", {})
        queries = settings.get("coupon_queries", DEFAULT_QUERIES)[:20]
        pages = max(1, min(3, int(settings.get("search_pages", 1))))
        out = []
        self.errors = {}
        # Sequential requests avoid bursting a search account's rate limit.
        for query in queries:
            for page in range(pages):
                try:
                    response = await client.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        headers={"X-Subscription-Token": key},
                        params={"q": query, "count": 20, "offset": page, "freshness": "pm"},
                        follow_redirects=False,
                    )
                    # Keep authentication tokens and request details out of public errors.
                    if response.status_code != 200:
                        self.errors[query] = f"Search HTTP {response.status_code}"
                        break
                    data = response.json()
                    for item in data.get("web", {}).get("results", []):
                        url = item.get("url", "")
                        if not item.get("title") or not public_link(url):
                            continue
                        out.append(RawOpportunity(
                            title=clean(item["title"]), url=url,
                            source="web_search/" + urlsplit(url).netloc,
                            description=clean(item.get("description", "")),
                            category="deals_shopping",
                        ))
                    if not data.get("query", {}).get("more_results_available", False):
                        break
                except (httpx.HTTPError, ValueError):
                    self.errors[query] = "Search request failed"
                    break
                finally:
                    await asyncio.sleep(1.1)
        return out


def coupon_sources() -> list[Source]:
    settings = load_profile().get("discovery", {})
    feeds = settings.get("coupon_feeds", DEFAULT_FEEDS)
    return [CouponFeed(spec) for spec in feeds] + [CouponSearch()]
