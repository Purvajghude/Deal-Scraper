# Project Hermes — Freebie Register

> **Mission: never again miss a valuable freebie on the internet.**

Hermes is a self-hosted board that continuously pulls **freebies and opportunities**
from across the internet — free AI API credits, student offers, government schemes
and yojanas, Indian shopping deals, free courses, hackathons, dev programs, betas —
and arranges everything **neatly, category-wise**, on one dashboard.

No AI ranking, no notification spam, no setup ceremony. Just the data, organized.

## Run it

```powershell
pip install -r requirements.txt
python -m hermes serve
```

Open **http://127.0.0.1:8787**. That's it — the server refreshes all sources on
startup and again every 6 hours by itself. The "Refresh sources" button pulls
on demand.

## What it watches

| Category | Sources |
|---|---|
| 🤖 AI & API credits | Hacker News (free API / open-weights / credits queries), Hugging Face blog, r/LocalLLaMA |
| 🎓 Student offers | **studentoffers.co** full verified catalog (~550 offers), GitHub blog |
| 🏛️ Govt schemes & yojanas | PIB (Press Information Bureau) releases, filtered for schemes/scholarships/benefits (Hindi + English), r/scholarships |
| 🛒 Deals & shopping | dealsheaven.in (Indian deals, bank offers), r/FREE, r/eFreebies, r/dealsforindia |
| 🍔 Food & dining | keyword-routed from deal sources (McD/KFC/Swiggy/Zomato/…) |
| 📚 Free courses | r/udemyfreebies, freeCodeCamp |
| 🏆 Hackathons | dev.to #hackathon, r/hackathon, HN |
| ☁️ Dev programs & cloud | GitHub blog, dev.to #opensource, HN free-tier/credits |
| 🧪 Beta & early access | Product Hunt, HN Show/early-access |

Adding a source = one file in `hermes/sources/` + one registry line.
Categories are assigned by deterministic keyword rules in `hermes/categorize.py`.

## Other commands

```powershell
python -m hermes discover            # one manual pull
python -m hermes digest              # category-wise digest in the terminal
python -m hermes mark <id> dismissed # hide an item forever (✕ on the dashboard does the same)
python -m hermes rank                # optional AI scoring (needs ANTHROPIC_API_KEY) — off by default
```

## Design docs

Full architecture, competitive research, and the longer-term roadmap (price
intelligence, browser assistant, notifications) live in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Those layers stay dormant until wanted.
