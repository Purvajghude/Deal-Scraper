from __future__ import annotations

from datetime import date

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator

from . import db
from .ui import PAGE

app = FastAPI(title="Ledger", version="0.1.0")


class TxIn(BaseModel):
    amount: float
    kind: str
    category: str
    note: str = ""
    method: str = "upi"
    occurred_on: str = ""

    @field_validator("kind")
    @classmethod
    def _kind(cls, v):
        if v not in ("income", "expense"):
            raise ValueError("kind must be income or expense")
        return v

    @field_validator("amount")
    @classmethod
    def _amount(cls, v):
        if v <= 0:
            raise ValueError("amount must be positive")
        return v


class BudgetIn(BaseModel):
    category: str
    monthly_limit: float | None


@app.get("/api/meta")
def api_meta():
    return {"expense_categories": db.EXPENSE_CATEGORIES,
            "income_categories": db.INCOME_CATEGORIES,
            "methods": db.METHODS,
            "today": date.today().isoformat()}


@app.get("/api/summary")
def api_summary(month: str | None = None):
    month = month or date.today().strftime("%Y-%m")
    con = db.connect()
    try:
        months = db.last_n_months(6)
        return {
            "month": month,
            "totals": db.month_totals(con, month),
            "by_category": db.by_category(con, month),
            "trend": db.trend(con, months),
            "budgets": db.budgets_with_spent(con, month),
        }
    finally:
        con.close()


@app.get("/api/transactions")
def api_transactions(month: str | None = None):
    month = month or date.today().strftime("%Y-%m")
    con = db.connect()
    try:
        return [dict(r) for r in db.month_transactions(con, month)]
    finally:
        con.close()


@app.post("/api/transactions")
def api_add(tx: TxIn):
    con = db.connect()
    try:
        tx_id = db.add_tx(con, tx.amount, tx.kind, tx.category, tx.note,
                          tx.method, tx.occurred_on or date.today().isoformat())
        return {"ok": True, "id": tx_id}
    finally:
        con.close()


@app.delete("/api/transactions/{tx_id}")
def api_delete(tx_id: int):
    con = db.connect()
    try:
        db.delete_tx(con, tx_id)
        return {"ok": True}
    finally:
        con.close()


@app.put("/api/budgets")
def api_budget(b: BudgetIn):
    con = db.connect()
    try:
        db.set_budget(con, b.category, b.monthly_limit)
        return {"ok": True}
    finally:
        con.close()


@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE
