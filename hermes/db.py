from __future__ import annotations

import hashlib
import re
import sqlite3

from .categorize import categorize
from .config import DB_PATH
from .models import RawOpportunity, Score, utcnow_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
  id            INTEGER PRIMARY KEY,
  fingerprint   TEXT UNIQUE NOT NULL,
  title         TEXT NOT NULL,
  url           TEXT NOT NULL,
  description   TEXT,
  source        TEXT NOT NULL,
  category      TEXT,
  region_hint   TEXT,
  posted_at     TEXT,
  discovered_at TEXT NOT NULL,
  deadline      TEXT,
  status        TEXT NOT NULL DEFAULT 'new'
);

CREATE TABLE IF NOT EXISTS scores (
  opportunity_id INTEGER PRIMARY KEY REFERENCES opportunities(id),
  scorer        TEXT NOT NULL,
  relevance     REAL, legitimacy REAL, confidence REAL,
  est_value_inr REAL, effort_hours REAL,
  eligibility   TEXT, region_scope TEXT, urgency TEXT,
  composite     REAL NOT NULL,
  reasoning     TEXT,
  scored_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS interactions (
  id INTEGER PRIMARY KEY,
  opportunity_id INTEGER REFERENCES opportunities(id),
  action TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_history (
  id INTEGER PRIMARY KEY,
  product_key TEXT NOT NULL,
  retailer TEXT NOT NULL,
  price_inr REAL NOT NULL,
  captured_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_opp_status ON opportunities(status);
CREATE INDEX IF NOT EXISTS idx_scores_composite ON scores(composite);
"""


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def fingerprint(opp: RawOpportunity) -> str:
    """Dedupe key: normalized URL, falling back to normalized title."""
    url = re.sub(r"[?#].*$", "", opp.url.strip().lower()).rstrip("/")
    title = re.sub(r"\W+", " ", opp.title.lower()).strip()
    return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:24]


def insert_opportunities(con: sqlite3.Connection, opps: list[RawOpportunity]) -> int:
    """Insert new opportunities; duplicates (same fingerprint) are skipped."""
    inserted = 0
    now = utcnow_iso()
    for opp in opps:
        try:
            con.execute(
                "INSERT INTO opportunities (fingerprint, title, url, description,"
                " source, category, region_hint, posted_at, discovered_at)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (fingerprint(opp), opp.title[:300], opp.url, opp.description[:2000],
                 opp.source, categorize(opp), opp.region_hint, opp.posted_at, now),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            pass
    con.commit()
    return inserted


def unranked(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return con.execute(
        "SELECT * FROM opportunities WHERE status = 'new' ORDER BY id"
    ).fetchall()


def save_score(con: sqlite3.Connection, opp_id: int, s: Score) -> None:
    con.execute(
        "INSERT OR REPLACE INTO scores (opportunity_id, scorer, relevance, legitimacy,"
        " confidence, est_value_inr, effort_hours, eligibility, region_scope, urgency,"
        " composite, reasoning, scored_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (opp_id, s.scorer, s.relevance, s.legitimacy, s.confidence, s.est_value_inr,
         s.effort_hours, s.eligibility, s.region_scope, s.urgency, s.composite,
         s.reasoning, s.scored_at),
    )
    con.execute("UPDATE opportunities SET status = 'ranked' WHERE id = ?", (opp_id,))
    con.commit()


def ranked(con: sqlite3.Connection, limit: int = 30) -> list[sqlite3.Row]:
    return con.execute(
        "SELECT o.*, s.* FROM opportunities o JOIN scores s ON s.opportunity_id = o.id"
        " WHERE o.status NOT IN ('dismissed', 'expired')"
        " ORDER BY s.composite DESC LIMIT ?",
        (limit,),
    ).fetchall()


def list_active(con: sqlite3.Connection, category: str | None = None,
                q: str | None = None, limit: int = 200) -> list[sqlite3.Row]:
    """Active opportunities, newest first. Scores are optional (LEFT JOIN)."""
    sql = (
        "SELECT o.*, s.composite, s.urgency FROM opportunities o"
        " LEFT JOIN scores s ON s.opportunity_id = o.id"
        " WHERE o.status NOT IN ('dismissed', 'expired')"
    )
    params: list = []
    if category:
        sql += " AND o.category = ?"
        params.append(category)
    if q:
        sql += " AND (o.title LIKE ? OR o.description LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    # newest batch first; alphabetical within a batch (catalog imports share a timestamp)
    sql += " ORDER BY o.discovered_at DESC, o.title COLLATE NOCASE ASC LIMIT ?"
    params.append(limit)
    return con.execute(sql, params).fetchall()


def category_counts(con: sqlite3.Connection) -> dict[str, int]:
    rows = con.execute(
        "SELECT category, COUNT(*) n FROM opportunities"
        " WHERE status NOT IN ('dismissed', 'expired') GROUP BY category"
    ).fetchall()
    return {r["category"]: r["n"] for r in rows}


def new_since(con: sqlite3.Connection, iso_ts: str) -> int:
    return con.execute(
        "SELECT COUNT(*) n FROM opportunities WHERE discovered_at > ?"
        " AND status NOT IN ('dismissed', 'expired')",
        (iso_ts,),
    ).fetchone()["n"]


def record_interaction(con: sqlite3.Connection, opp_id: int, action: str) -> None:
    con.execute(
        "INSERT INTO interactions (opportunity_id, action, created_at) VALUES (?,?,?)",
        (opp_id, action, utcnow_iso()),
    )
    if action in ("redeemed", "dismissed"):
        con.execute("UPDATE opportunities SET status = ? WHERE id = ?", (action, opp_id))
    con.commit()


def category_weights(con: sqlite3.Connection) -> dict[str, float]:
    """Learned multiplier per category from redeem/dismiss history, clamped to [0.5, 1.5]."""
    rows = con.execute(
        "SELECT o.category, i.action, COUNT(*) AS n FROM interactions i"
        " JOIN opportunities o ON o.id = i.opportunity_id"
        " WHERE i.action IN ('redeemed', 'dismissed') GROUP BY o.category, i.action"
    ).fetchall()
    tally: dict[str, dict[str, int]] = {}
    for r in rows:
        tally.setdefault(r["category"], {})[r["action"]] = r["n"]
    weights = {}
    for cat, t in tally.items():
        good, bad = t.get("redeemed", 0), t.get("dismissed", 0)
        weights[cat] = max(0.5, min(1.5, 1.0 + 0.1 * (good - bad)))
    return weights
