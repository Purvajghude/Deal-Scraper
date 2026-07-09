from __future__ import annotations

import sqlite3

from .categorize import CATEGORIES
from .db import list_active


def render_digest(con: sqlite3.Connection, per_category: int = 6) -> str:
    lines = ["HERMES FREEBIE REGISTER", "=" * 60]
    empty = True
    for slug, (name, emoji) in CATEGORIES.items():
        rows = list_active(con, category=slug, limit=per_category)
        if not rows:
            continue
        empty = False
        lines += ["", f"{emoji} {name.upper()}", "-" * 40]
        for r in rows:
            lines.append(f"  • {r['title'][:90]}")
            lines.append(f"    {r['url']}   (via {r['source']})   [id {r['id']}]")
    if empty:
        return "Nothing discovered yet. Run: python -m hermes discover"
    lines += ["", "Dismiss noise:  python -m hermes mark <id> dismissed"]
    return "\n".join(lines)
