"""Discovery source registry. To add a source: subclass Source, list it here."""

from __future__ import annotations

import asyncio

import httpx

from ..models import RawOpportunity
from .base import HEADERS, Source
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


async def discover_all() -> tuple[list[RawOpportunity], dict[str, str]]:
    """Run every source concurrently. Returns (opportunities, per-source errors)."""
    errors: dict[str, str] = {}
    async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
        results = await asyncio.gather(
            *(src.fetch(client) for src in REGISTRY), return_exceptions=True
        )
    opps: list[RawOpportunity] = []
    for src, res in zip(REGISTRY, results):
        if isinstance(res, BaseException):
            errors[src.name] = f"{type(res).__name__}: {res}"
        else:
            opps.extend(res)
    return opps, errors
