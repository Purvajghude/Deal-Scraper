# Project Hermes + Ledger

Two self-hosted apps in one repo:

- **Hermes** — an AI-powered opportunity-intelligence platform that continuously
  discovers, ranks, and presents freebies (AI credits, student offers, govt
  yojanas, Indian deals, hackathons, courses…) on one command-center dashboard,
  with Telegram alerts, price tracking, and a browser assistant. India-first.
- **Ledger** — a personal finance tracker with a beautiful dashboard for your
  income, expenses, budgets, and six-month cash flow.

---

## Hermes — Opportunity Intelligence

```powershell
pip install -r requirements.txt
python -m hermes serve          # http://127.0.0.1:8787
```

The server runs the whole pipeline on startup and every 6 hours by itself:

```
discover (7 sources) → dedupe → rank (Claude or heuristic) → notify (Telegram) → price-check
```

**Full feature set (v0.3):**

| Feature | What it does |
|---|---|
| **Discovery** | 7 sources: Hacker News, Reddit (RSS), curated RSS (HuggingFace, ProductHunt, GitHub, dev.to, freeCodeCamp), studentoffers.co catalog (~550 offers), dealsheaven.in, PIB govt schemes, Devpost hackathons |
| **Categories** | 9 auto-assigned by keyword rules: AI credits · student offers · govt schemes · deals · food · courses · hackathons · dev programs · betas |
| **AI ranking** | `claude-opus-4-8` scores relevance/legitimacy/value/effort/eligibility/urgency when `ANTHROPIC_API_KEY` is set; deterministic heuristic fallback otherwise. Toggle "smart" sort on the dashboard. |
| **Command center** | Stats strip (live count, new-24h, ranked, price alerts, value realized), category tabs, instant search, ✓ redeemed / ✕ dismiss with a learning loop |
| **Price intelligence** | Watch any product URL → records price every cycle → **BUY / GOOD / WAIT** verdict vs recorded median/low, with sparklines (Price watch tab) |
| **Telegram alerts** | High-urgency finds pushed to your phone (configure in `profile.yaml`; silent no-op until then) |
| **Browser assistant** | `extension/` — MV3 extension: price-watch button + matching offers overlay on Amazon.in / Flipkart product pages, plus a search popup. Load unpacked, pointed at the local API. |
| **Docker** | `docker compose up` — containerized, self-hosting, data in a named volume |

Personalize via [`profile.yaml`](profile.yaml). Adding a source = one file in
`hermes/sources/` + one registry line.

Other commands: `python -m hermes discover|digest|rank`, `python -m hermes mark <id> dismissed`.

---

## Ledger — Personal Finance Tracker

```powershell
python -m finance seed          # optional: load sample data to explore
python -m finance serve         # http://127.0.0.1:8899
```

- **Track** income and expenses with category, payment method, note, and date —
  fast inline entry.
- **See** your net for the month, six-month cash-flow chart, and where the money
  went (category breakdown with real ₹ labels).
- **Budget** per category with progress bars that flag over-spending.
- **Navigate** month by month.

Beautiful "evening ledger" design — deep green paper, serif numerals, hairline
rules. Chart colors are accessibility-validated (colorblind-safe on the dark
surface). Data lives in `finance.db`; nothing leaves your machine.

---

## Architecture & design

Full competitive research, system design, database schema, AI pipeline, and the
milestone roadmap for both apps: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
