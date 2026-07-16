from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("FINANCE_DB", Path(__file__).resolve().parent.parent / "finance.db"))

EXPENSE_CATEGORIES = ["food", "travel", "shopping", "bills", "entertainment",
                      "education", "health", "rent", "other"]
INCOME_CATEGORIES = ["salary", "stipend", "freelance", "cashback", "gift", "other"]
METHODS = ["upi", "card", "cash", "netbanking"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY,
  amount REAL NOT NULL CHECK (amount > 0),
  kind TEXT NOT NULL CHECK (kind IN ('income', 'expense')),
  category TEXT NOT NULL,
  note TEXT DEFAULT '',
  method TEXT DEFAULT 'upi',
  occurred_on TEXT NOT NULL,          -- YYYY-MM-DD
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(occurred_on);

CREATE TABLE IF NOT EXISTS budgets (
  category TEXT PRIMARY KEY,
  monthly_limit REAL NOT NULL CHECK (monthly_limit > 0)
);
"""


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def add_tx(con: sqlite3.Connection, amount: float, kind: str, category: str,
           note: str, method: str, occurred_on: str) -> int:
    cur = con.execute(
        "INSERT INTO transactions (amount, kind, category, note, method, occurred_on, created_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (amount, kind, category, note.strip()[:200], method, occurred_on,
         datetime.now(timezone.utc).isoformat(timespec="seconds")),
    )
    con.commit()
    return cur.lastrowid


def delete_tx(con: sqlite3.Connection, tx_id: int) -> None:
    con.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    con.commit()


def month_transactions(con: sqlite3.Connection, month: str) -> list[sqlite3.Row]:
    return con.execute(
        "SELECT * FROM transactions WHERE occurred_on LIKE ? ORDER BY occurred_on DESC, id DESC",
        (f"{month}-%",),
    ).fetchall()


def month_totals(con: sqlite3.Connection, month: str) -> dict:
    row = con.execute(
        "SELECT COALESCE(SUM(CASE WHEN kind='income' THEN amount END),0) AS income,"
        " COALESCE(SUM(CASE WHEN kind='expense' THEN amount END),0) AS expense"
        " FROM transactions WHERE occurred_on LIKE ?",
        (f"{month}-%",),
    ).fetchone()
    return {"income": row["income"], "expense": row["expense"],
            "net": row["income"] - row["expense"]}


def by_category(con: sqlite3.Connection, month: str) -> list[dict]:
    rows = con.execute(
        "SELECT category, SUM(amount) AS total, COUNT(*) AS n FROM transactions"
        " WHERE kind='expense' AND occurred_on LIKE ? GROUP BY category ORDER BY total DESC",
        (f"{month}-%",),
    ).fetchall()
    return [dict(r) for r in rows]


def trend(con: sqlite3.Connection, months: list[str]) -> list[dict]:
    out = []
    for m in months:
        t = month_totals(con, m)
        out.append({"month": m, **t})
    return out


def set_budget(con: sqlite3.Connection, category: str, limit: float | None) -> None:
    if limit is None or limit <= 0:
        con.execute("DELETE FROM budgets WHERE category = ?", (category,))
    else:
        con.execute(
            "INSERT INTO budgets (category, monthly_limit) VALUES (?,?)"
            " ON CONFLICT(category) DO UPDATE SET monthly_limit = excluded.monthly_limit",
            (category, limit),
        )
    con.commit()


def budgets_with_spent(con: sqlite3.Connection, month: str) -> list[dict]:
    spent = {r["category"]: r["total"] for r in by_category(con, month)}
    rows = con.execute("SELECT * FROM budgets ORDER BY category").fetchall()
    return [{"category": r["category"], "limit": r["monthly_limit"],
             "spent": spent.get(r["category"], 0.0)} for r in rows]


def last_n_months(n: int, today: date | None = None) -> list[str]:
    today = today or date.today()
    y, m = today.year, today.month
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))
