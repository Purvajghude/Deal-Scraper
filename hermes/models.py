from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class RawOpportunity:
    """What a discovery source emits. Normalization/dedupe happens downstream."""

    title: str
    url: str
    source: str
    description: str = ""
    category: str = "unknown"       # source-level hint; categorizer finalizes it
    category_pinned: bool = False   # True = source curates this category; skip keyword routing
    region_hint: str = "global"
    posted_at: str = ""             # ISO 8601 when known


@dataclass
class Score:
    scorer: str
    relevance: float
    legitimacy: float
    confidence: float
    est_value_inr: float
    effort_hours: float
    eligibility: str            # eligible | likely | unlikely | no
    region_scope: str           # global | india | maharashtra | mumbai | other
    urgency: str                # critical | high | medium | low
    composite: float
    reasoning: str
    scored_at: str = field(default_factory=utcnow_iso)
