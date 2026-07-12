"""Price intelligence — watch products, record history, judge discounts.

Add any product URL (Amazon.in, Flipkart, Croma, ...) to the watchlist; every
refresh cycle re-fetches the price and appends to price_history. The verdict
compares the current price against the recorded median/minimum so a "50% OFF!"
banner can be checked against reality.

Extraction is best-effort: JSON-LD offers, then og/meta price tags, then the
first ₹-amount near the top of the page. Retailers that hard-block bots simply
record nothing for that cycle.
"""

from __future__ import annotations

import json
import re
import sqlite3
import statistics
from urllib.parse import urlparse

import httpx

from .models import utcnow_iso
from .sources.base import BROWSER_HEADERS

WATCHLIST_SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
  id INTEGER PRIMARY KEY,
  url TEXT UNIQUE NOT NULL,
  label TEXT NOT NULL,
  target_price REAL,
  created_at TEXT NOT NULL
);
"""

PRICE_PATTERNS = [
    re.compile(r'"price"\s*:\s*"?([\d,]+(?:\.\d{1,2})?)"?'),
    re.compile(r'property="(?:og:price:amount|product:price:amount)"\s+content="([\d,.]+)"'),
    re.compile(r'itemprop="price"[^>]*content="([\d,.]+)"'),
    re.compile(r'[₹]\s*([\d,]{2,12}(?:\.\d{1,2})?)'),
    re.compile(r'Rs\.?\s*([\d,]{2,12}(?:\.\d{1,2})?)'),
]


def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(WATCHLIST_SCHEMA)


def _parse_amount(raw: str) -> float | None:
    try:
        v = float(raw.replace(",", ""))
    except ValueError:
        return None
    return v if 10 <= v <= 10_000_000 else None  # sanity window for INR prices


def extract_price(html: str) -> float | None:
    # JSON-LD product blocks first — most reliable when present
    for block in re.findall(
        r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S
    )[:5]:
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            offers = item.get("offers") if isinstance(item, dict) else None
            if isinstance(offers, list) and offers:
                offers = offers[0]
            if isinstance(offers, dict):
                v = _parse_amount(str(offers.get("price", "")))
                if v:
                    return v
    for pat in PRICE_PATTERNS:
        m = pat.search(html)
        if m:
            v = _parse_amount(m.group(1))
            if v:
                return v
    return None


async def fetch_price(client: httpx.AsyncClient, url: str) -> float | None:
    try:
        r = await client.get(url, headers=BROWSER_HEADERS, follow_redirects=True)
        if r.status_code != 200:
            return None
        return extract_price(r.text)
    except httpx.HTTPError:
        return None


def record_price(con: sqlite3.Connection, watch_id: int, url: str, price: float) -> None:
    con.execute(
        "INSERT INTO price_history (product_key, retailer, price_inr, captured_at)"
        " VALUES (?,?,?,?)",
        (str(watch_id), urlparse(url).netloc, price, utcnow_iso()),
    )
    con.commit()


def history(con: sqlite3.Connection, watch_id: int, limit: int = 90) -> list[dict]:
    rows = con.execute(
        "SELECT price_inr, captured_at FROM price_history WHERE product_key = ?"
        " ORDER BY captured_at DESC LIMIT ?",
        (str(watch_id), limit),
    ).fetchall()
    return [dict(r) for r in reversed(rows)]


def verdict(prices: list[float], target: float | None) -> dict:
    """Buy/wait judgment from recorded history."""
    if not prices:
        return {"verdict": "no data", "detail": "no price captured yet"}
    current = prices[-1]
    if target and current <= target:
        return {"verdict": "BUY", "detail": f"at/below your ₹{target:,.0f} target"}
    if len(prices) < 3:
        return {"verdict": "watching", "detail": f"₹{current:,.0f} — need more history"}
    med, lo = statistics.median(prices), min(prices)
    if current <= lo * 1.02:
        return {"verdict": "BUY", "detail": f"at its recorded low (median ₹{med:,.0f})"}
    if current < med * 0.93:
        return {"verdict": "GOOD", "detail": f"{(1 - current / med) * 100:.0f}% below median ₹{med:,.0f}"}
    if current > med * 1.05:
        return {"verdict": "WAIT", "detail": f"above median ₹{med:,.0f}; low was ₹{lo:,.0f}"}
    return {"verdict": "typical", "detail": f"around median ₹{med:,.0f}; low was ₹{lo:,.0f}"}


async def check_all(con: sqlite3.Connection) -> int:
    """Re-fetch every watched product. Returns how many prices were recorded."""
    ensure_schema(con)
    rows = con.execute("SELECT * FROM watchlist").fetchall()
    if not rows:
        return 0
    recorded = 0
    async with httpx.AsyncClient(timeout=25) as client:
        for w in rows:
            price = await fetch_price(client, w["url"])
            if price is not None:
                record_price(con, w["id"], w["url"], price)
                recorded += 1
    return recorded
