"""Discovery source registry. To add a source: subclass Source, list it here."""

from __future__ import annotations

import asyncio
import os
import time

import httpx

from ..models import RawOpportunity
from .base import HEADERS, Source
from .coupons import coupon_sources
from .dealsheaven import DealsHeaven
from .devpost import Devpost
from .govt import GovtSchemes
from .hackernews import HackerNews
from .reddit import Reddit
from .rss import RSS
from .studentoffers import StudentOffers

REGISTRY: list[Source] = [
    HackerNews(), Reddit(), RSS(), StudentOffers(), DealsHeaven(), GovtSchemes(),
    Devpost(),
]
SOURCE_STATUS: dict[str, dict] = {}


async def discover_all() -> tuple[list[RawOpportunity], dict[str, str]]:
    """Run every source concurrently. Returns (opportunities, per-source errors)."""
    errors: dict[str, str] = {}
    sources = REGISTRY + coupon_sources()
    async def fetch_one(src):
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(src.fetch(client), timeout=120)
            partial = getattr(src, "errors", {})
            disabled = src.name == "coupon_web_search" and not os.getenv("BRAVE_SEARCH_API_KEY")
            SOURCE_STATUS[src.name] = {
                "status": "disabled" if disabled else "partial" if partial else "ok" if result else "empty",
                "count": len(result), "seconds": round(time.monotonic() - start, 1),
                "detail": "Set BRAVE_SEARCH_API_KEY to enable internet search" if disabled else "; ".join(partial.values()),
            }
            for name, error in partial.items():
                errors[f"{src.name}/{name}"] = error
            return result
        except Exception as exc:
            SOURCE_STATUS[src.name] = {"status": "error", "count": 0, "detail": str(exc), "seconds": round(time.monotonic() - start, 1)}
            raise
    async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
        results = await asyncio.gather(
            *(fetch_one(src) for src in sources), return_exceptions=True
        )
    opps: list[RawOpportunity] = []
    for src, res in zip(sources, results):
        if isinstance(res, BaseException):
            errors[src.name] = f"{type(res).__name__}: {res}"
        else:
            opps.extend(res)
    return opps, errors
