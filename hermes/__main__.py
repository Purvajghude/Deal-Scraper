from __future__ import annotations

import asyncio
import sys

# Windows consoles default to cp1252, which can't print ₹ — force UTF-8.
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from . import db
from .digest import render_digest

USAGE = """Hermes — freebie register

  python -m hermes serve [port]       dashboard at http://127.0.0.1:8787
                                      (auto-refreshes sources every 6 hours)
  python -m hermes discover           pull fresh opportunities once, manually
  python -m hermes digest             category-wise digest in the terminal
  python -m hermes mark <id> <action> redeemed | dismissed | save
  python -m hermes rank               optional: AI-score items (needs ANTHROPIC_API_KEY)
"""


def cmd_discover() -> None:
    from .sources import discover_all

    opps, errors = asyncio.run(discover_all())
    con = db.connect()
    try:
        inserted = db.insert_opportunities(con, opps)
    finally:
        con.close()
    print(f"Fetched {len(opps)} candidates, {inserted} new (rest were duplicates).")
    for name, err in errors.items():
        print(f"  warning: source '{name}' failed: {err}")


def cmd_rank() -> None:
    from .rank import rank_all

    con = db.connect()
    try:
        count, scorer = rank_all(con)
    finally:
        con.close()
    print(f"Ranked {count} opportunities using {scorer}.")


def cmd_digest() -> None:
    con = db.connect()
    try:
        print(render_digest(con))
    finally:
        con.close()


def cmd_serve(port: int = 8787) -> None:
    import uvicorn

    uvicorn.run("hermes.api:app", host="127.0.0.1", port=port)


def cmd_mark(opp_id: int, action: str) -> None:
    if action not in ("redeemed", "dismissed", "save", "click"):
        sys.exit(f"unknown action '{action}' — use redeemed | dismissed | save")
    con = db.connect()
    try:
        db.record_interaction(con, opp_id, action)
    finally:
        con.close()
    print(f"Recorded {action} for opportunity {opp_id}. Future ranking will adapt.")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(USAGE)
        return
    cmd = args[0]
    if cmd == "discover":
        cmd_discover()
    elif cmd == "rank":
        cmd_rank()
    elif cmd == "digest":
        cmd_digest()
    elif cmd == "serve":
        cmd_serve(int(args[1]) if len(args) > 1 else 8787)
    elif cmd == "mark" and len(args) >= 3:
        cmd_mark(int(args[1]), args[2])
    else:
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
