from __future__ import annotations

import sys

USAGE = """Ledger — personal finance tracker

  python -m finance serve [port]   dashboard at http://127.0.0.1:8899
  python -m finance seed           load a month of sample data (for trying it out)
"""


def cmd_serve(port: int = 8899) -> None:
    import uvicorn

    uvicorn.run("finance.api:app", host="127.0.0.1", port=port)


def cmd_seed() -> None:
    """Realistic sample data so the dashboard isn't a blank page on first open."""
    import random
    from datetime import date, timedelta

    from . import db

    con = db.connect()
    today = date.today()
    rng = random.Random(7)
    samples = [
        ("income", "stipend", 12000, "monthly stipend", "netbanking"),
        ("income", "freelance", 8500, "landing page gig", "upi"),
        ("expense", "rent", 7000, "hostel/PG rent", "upi"),
        ("expense", "food", 180, "hostel mess top-up", "upi"),
        ("expense", "food", 240, "Zomato", "upi"),
        ("expense", "food", 320, "dinner with team", "upi"),
        ("expense", "travel", 150, "metro card recharge", "upi"),
        ("expense", "bills", 349, "Jio recharge", "upi"),
        ("expense", "education", 499, "Udemy course", "card"),
        ("expense", "entertainment", 199, "movie", "upi"),
        ("expense", "shopping", 1299, "keyboard", "card"),
    ]
    n = 0
    for months_back in range(5, -1, -1):
        anchor = (today.replace(day=15) - timedelta(days=30 * months_back))
        for kind, cat, amt, note, method in samples:
            jitter = rng.uniform(0.8, 1.25)
            d = anchor.replace(day=min(28, rng.randint(1, 28)))
            db.add_tx(con, round(amt * jitter, 2), kind, cat, note, method, d.isoformat())
            n += 1
    db.set_budget(con, "food", 3000)
    db.set_budget(con, "entertainment", 800)
    db.set_budget(con, "shopping", 2000)
    con.close()
    print(f"Seeded {n} sample transactions + 3 budgets into {db.DB_PATH}")
    print("Delete rows from the dashboard, or delete finance.db to start clean.")


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] == "serve":
        cmd_serve(int(args[1]) if len(args) > 1 else 8899)
    elif args[0] == "seed":
        cmd_seed()
    else:
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
