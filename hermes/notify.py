"""Notifications — Telegram first (free, instant, works on any phone).

Configure in profile.yaml:

    notifications:
      telegram:
        bot_token: "123456:ABC..."   # from @BotFather
        chat_id: "123456789"          # from @userinfobot
      min_urgency: high               # critical | high | medium | low

Unconfigured -> everything degrades to a silent no-op; the dashboard still
shows everything. Alerts fire only for NEW items at/above min_urgency, and
each opportunity is notified at most once (tracked in the interactions table).
"""

from __future__ import annotations

import sqlite3

import httpx

from .config import load_profile
from .models import utcnow_iso

URGENCY_ORDER = {"critical": 3, "high": 2, "medium": 1, "low": 0}


def telegram_config() -> tuple[str, str, str] | None:
    """(bot_token, chat_id, min_urgency) or None when not configured."""
    cfg = (load_profile().get("notifications") or {})
    tg = cfg.get("telegram") or {}
    token, chat = tg.get("bot_token", ""), str(tg.get("chat_id", ""))
    if not token or not chat:
        return None
    return token, chat, cfg.get("min_urgency", "high")


def _already_notified(con: sqlite3.Connection, opp_id: int) -> bool:
    return con.execute(
        "SELECT 1 FROM interactions WHERE opportunity_id = ? AND action = 'notified'",
        (opp_id,),
    ).fetchone() is not None


def _mark_notified(con: sqlite3.Connection, opp_id: int) -> None:
    con.execute(
        "INSERT INTO interactions (opportunity_id, action, created_at) VALUES (?, 'notified', ?)",
        (opp_id, utcnow_iso()),
    )
    con.commit()


async def send_telegram(token: str, chat_id: str, text: str) -> bool:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                  "disable_web_page_preview": True},
        )
        return r.status_code == 200


async def notify_new(con: sqlite3.Connection, limit: int = 10) -> int:
    """Alert on ranked items at/above min_urgency that haven't been notified.

    Returns the number of alerts sent. No-op without Telegram config or when
    nothing qualifies.
    """
    cfg = telegram_config()
    if cfg is None:
        return 0
    token, chat_id, min_urgency = cfg
    floor = URGENCY_ORDER.get(min_urgency, 2)

    rows = con.execute(
        "SELECT o.id, o.title, o.url, o.category, s.urgency, s.est_value_inr, s.reasoning"
        " FROM opportunities o JOIN scores s ON s.opportunity_id = o.id"
        " WHERE o.status = 'ranked' ORDER BY s.composite DESC LIMIT 100"
    ).fetchall()

    sent = 0
    for r in rows:
        if sent >= limit:
            break
        if URGENCY_ORDER.get(r["urgency"], 0) < floor or _already_notified(con, r["id"]):
            continue
        icon = "🚨" if r["urgency"] == "critical" else "⚡"
        value = f" · ~₹{r['est_value_inr']:,.0f}" if r["est_value_inr"] else ""
        text = (f"{icon} <b>{r['title'][:150]}</b>\n"
                f"{r['category']}{value}\n{r['reasoning'] or ''}\n{r['url']}")
        if await send_telegram(token, chat_id, text):
            _mark_notified(con, r["id"])
            sent += 1
    return sent
