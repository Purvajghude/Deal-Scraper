"""FastAPI server: command-center dashboard + self-running pipeline.

Every cycle (startup + every REFRESH_HOURS + the Refresh button):
  1. discover  — pull all sources
  2. rank      — AI scoring via Claude when credentials resolve, else heuristic
  3. notify    — Telegram alerts for high-urgency finds (if configured)
  4. prices    — re-check every watched product

Each stage degrades gracefully: no API key -> heuristic scores; no Telegram
config -> no alerts; empty watchlist -> skip. The dashboard works regardless.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from . import db, prices
from .categorize import CATEGORIES
from .dashboard import PAGE
from .models import utcnow_iso

REFRESH_HOURS = 6

_state = {
    "running": False, "stage": "", "last_run": None, "last_new": 0,
    "last_scorer": "", "last_notified": 0, "last_prices": 0, "last_errors": {},
}
_refresh_lock = asyncio.Lock()


async def _run_pipeline() -> None:
    from .notify import notify_new
    from .rank import rank_all
    from .sources import discover_all

    if _refresh_lock.locked():
        return
    async with _refresh_lock:
        _state["running"] = True
        try:
            _state["stage"] = "discovering"
            opps, errors = await discover_all()
            con = db.connect()
            try:
                _state["last_new"] = db.insert_opportunities(con, opps)
                _state["last_errors"] = errors

                _state["stage"] = "ranking"

                def _rank_in_thread() -> str:
                    # sqlite connections are thread-bound — open a fresh one here
                    tcon = db.connect()
                    try:
                        _, scorer = rank_all(tcon)
                        return scorer
                    finally:
                        tcon.close()

                _state["last_scorer"] = await asyncio.to_thread(_rank_in_thread)

                _state["stage"] = "notifying"
                _state["last_notified"] = await notify_new(con)

                _state["stage"] = "checking prices"
                _state["last_prices"] = await prices.check_all(con)
            finally:
                con.close()
            _state["last_run"] = utcnow_iso()
        finally:
            _state["running"] = False
            _state["stage"] = ""


async def _loop() -> None:
    while True:
        try:
            await _run_pipeline()
        except Exception as e:
            _state["last_errors"] = {"pipeline": repr(e)}
            _state["running"] = False
        await asyncio.sleep(REFRESH_HOURS * 3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_loop())
    yield
    task.cancel()


app = FastAPI(title="Hermes", version="0.3.0", lifespan=lifespan)
# The browser extension (chrome-extension:// origin) talks to this local API.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── opportunities ────────────────────────────────────────────────────────────

@app.get("/api/categories")
def api_categories():
    con = db.connect()
    try:
        counts = db.category_counts(con)
    finally:
        con.close()
    return [
        {"slug": slug, "name": name, "emoji": emoji, "count": counts.get(slug, 0)}
        for slug, (name, emoji) in CATEGORIES.items()
    ]


@app.get("/api/opportunities")
def api_opportunities(category: str | None = None, q: str | None = None,
                      sort: str = "new", limit: int = 300):
    con = db.connect()
    try:
        rows = [dict(r) for r in db.list_active(con, category, q, limit)]
    finally:
        con.close()
    if sort == "smart":
        rows.sort(key=lambda r: (r.get("composite") or 0), reverse=True)
    return rows


@app.post("/api/opportunities/{opp_id}/{action}")
def api_mark(opp_id: int, action: str):
    if action not in ("click", "save", "redeemed", "dismissed"):
        return {"ok": False, "error": "unknown action"}
    con = db.connect()
    try:
        db.record_interaction(con, opp_id, action)
        return {"ok": True}
    finally:
        con.close()


# ── price watchlist ──────────────────────────────────────────────────────────

class WatchItem(BaseModel):
    url: str
    label: str
    target_price: float | None = None


@app.get("/api/watchlist")
def api_watchlist():
    con = db.connect()
    try:
        prices.ensure_schema(con)
        out = []
        for w in con.execute("SELECT * FROM watchlist ORDER BY id DESC").fetchall():
            hist = prices.history(con, w["id"])
            vals = [h["price_inr"] for h in hist]
            out.append({**dict(w), "history": hist,
                        "current": vals[-1] if vals else None,
                        **prices.verdict(vals, w["target_price"])})
        return out
    finally:
        con.close()


@app.post("/api/watchlist")
async def api_watch_add(item: WatchItem):
    con = db.connect()
    try:
        prices.ensure_schema(con)
        try:
            cur = con.execute(
                "INSERT INTO watchlist (url, label, target_price, created_at) VALUES (?,?,?,?)",
                (item.url.strip(), item.label.strip(), item.target_price, utcnow_iso()),
            )
            con.commit()
        except Exception:
            return {"ok": False, "error": "already watching this URL"}
        watch_id = cur.lastrowid
        # first price check immediately so the row isn't empty
        import httpx
        async with httpx.AsyncClient(timeout=25) as client:
            price = await prices.fetch_price(client, item.url)
        if price is not None:
            prices.record_price(con, watch_id, item.url, price)
        return {"ok": True, "id": watch_id, "first_price": price}
    finally:
        con.close()


@app.delete("/api/watchlist/{watch_id}")
def api_watch_delete(watch_id: int):
    con = db.connect()
    try:
        con.execute("DELETE FROM watchlist WHERE id = ?", (watch_id,))
        con.execute("DELETE FROM price_history WHERE product_key = ?", (str(watch_id),))
        con.commit()
        return {"ok": True}
    finally:
        con.close()


# ── extension lookups ────────────────────────────────────────────────────────

@app.get("/api/assist")
def api_assist(q: str):
    """Browser-assistant lookup: matching offers for a brand/product name."""
    con = db.connect()
    try:
        rows = db.list_active(con, q=q, limit=8)
        return [{"id": r["id"], "title": r["title"], "url": r["url"],
                 "category": r["category"]} for r in rows]
    finally:
        con.close()


# ── status ───────────────────────────────────────────────────────────────────

@app.get("/api/status")
def api_status():
    con = db.connect()
    try:
        day_ago = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="seconds")
        total = con.execute(
            "SELECT COUNT(*) c FROM opportunities WHERE status NOT IN ('dismissed','expired')"
        ).fetchone()["c"]
        ranked = con.execute("SELECT COUNT(*) c FROM scores").fetchone()["c"]
        redeemed_value = con.execute(
            "SELECT COALESCE(SUM(s.est_value_inr),0) v FROM scores s"
            " JOIN opportunities o ON o.id = s.opportunity_id WHERE o.status = 'redeemed'"
        ).fetchone()["v"]
        return {
            "total": total, "new_24h": db.new_since(con, day_ago),
            "ranked": ranked, "value_realized_inr": redeemed_value,
            "refresh": _state,
        }
    finally:
        con.close()


@app.post("/api/refresh")
async def api_refresh():
    if _state["running"]:
        return {"started": False, "reason": "already running"}
    asyncio.create_task(_run_pipeline())
    return {"started": True}


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return PAGE
