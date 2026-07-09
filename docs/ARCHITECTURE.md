# Hermes — System Architecture

*Founding architecture document. Last updated: 2026-07-09.*

> **Product pivot (2026-07-09, owner decision):** Hermes v0.2 is a **simple,
> category-wise freebie register** — breadth of sources + a clean dashboard,
> nothing else in the loop. AI ranking (`hermes/rank.py`) still exists but is
> optional and off by default; Telegram/notification plumbing, price history,
> and the browser extension are **deferred, not deleted** — the designs below
> remain the reference for when they're wanted. What shipped instead of
> M2–M6-as-planned: six live sources across nine categories (incl. govt
> schemes via PIB and the studentoffers.co catalog), a deterministic keyword
> categorizer, and a self-refreshing dashboard (6-hour cycle + manual button).

---

## 1. Ecosystem research — what exists, and what's missing

| Category | Representatives | Strengths | Gaps Hermes exploits |
|---|---|---|---|
| Amazon price trackers | Keepa, CamelCamelCamel | Deep price history, fake-discount detection | Amazon-only; no career/education opportunities; US-centric |
| Coupon extensions | Honey/PayPal Rewards, Karma | Auto-apply codes at 30k–100k stores, cashback | Reactive (only when you're already shopping); zero personalization of *what* to buy; no India bank/UPI offers |
| Indian cashback portals | CashKaro, GrabOn, CouponDunia | India coverage, bank-offer listings, some price history | Listing sites, not agents — you must go look; noisy; no ranking, no deadlines, no non-commerce opportunities |
| Student/dev opportunity platforms | Unstop, Devfolio, MLH, HackerEarth | Verified hackathons, scholarships, competitions in India | Each is one silo; you must check each site; no cross-platform ranking against *your* profile |
| Open-source price trackers | PriceBuddy, PriceGhost, Discount-Bandit | Self-hosted, URL-watch alerts | Track only URLs you already found; no discovery; no AI evaluation |

**The structural gap:** every existing product is a *single vertical* (prices OR coupons OR
hackathons) and every one is *pull-based* (you go to it). Nothing unifies commerce +
career + education opportunities, nothing ranks them against a personal profile with AI,
and nothing is India-first about banks/UPI/regional eligibility. That whole-person,
push-based, self-hosted intelligence layer is Hermes.

Sources: [Karma price-tracker comparison](https://www.karmanow.com/the-blog/top/the-best-price-trackers),
[Keepa vs CamelCamelCamel vs Honey](https://taskmonkey.ai/blog/amazon-price-tracker/keepa-vs-camelcamelcamel-vs-honey),
[NerdWallet coupon extensions](https://www.nerdwallet.com/finance/learn/browser-extensions-online-shopping),
[PriceBuddy](https://github.com/jez500/pricebuddy), [Discount-Bandit](https://github.com/Cybrarist/Discount-Bandit),
[Unstop](https://unstop.com/hackathons), [Devfolio](https://devfolio.co/hackathons),
[CashKaro](https://cashkaro.com/), [GrabOn](https://www.grabon.in/flipkart-coupons/).

## 2. Product vision

**One inbox for everything valuable.** Hermes maximizes value received over time, not
links collected. Success metric: `value_realized` (₹ saved + ₹ earned + credits obtained
+ opportunities won) and `regret_rate` (valuable things that expired unseen → drive to 0).

Differentiators, in priority order:
1. **Breadth** — commerce deals *and* hackathons/scholarships/credits/grants in one ranked feed.
2. **AI judgment** — every item scored for relevance, legitimacy, value, effort, eligibility, urgency.
3. **India-first** — eligibility detection (Global / India / Maharashtra / Mumbai), ₹ display, bank/UPI/card offer awareness, Indian sale-season calendar.
4. **Learning** — clicks/redemptions/dismissals continuously reshape ranking.
5. **Self-hosted & private** — your purchase and interest graph never leaves your machine.

## 3. System architecture

```
┌──────────────────────────── HERMES ────────────────────────────────┐
│                                                                    │
│  profile.yaml ──────────────┐                                      │
│                             ▼                                      │
│  ┌─ DISCOVERY ─┐   ┌─ NORMALIZE ─┐   ┌─ INTELLIGENCE ─┐            │
│  │ Source      │   │ dedupe by   │   │ Claude Opus    │            │
│  │ plugins     │──▶│ URL + title │──▶│ 4.8 batch      │            │
│  │ (async)     │   │ simhash     │   │ scoring        │            │
│  └─────────────┘   └─────────────┘   └───────┬────────┘            │
│        ▲                                     ▼                     │
│  scheduler (cron /            ┌── SQLite: opportunities, scores,   │
│  `hermes discover`)           │   interactions, price_history      │
│                               ▼                                    │
│  ┌─ PRESENTATION ────────────────────────────────────────┐         │
│  │ FastAPI dashboard · terminal digest · (v2: Telegram)  │         │
│  └───────────────────────────────────────────────────────┘         │
│                               ▲                                    │
│  ┌─ LEARNING ─┐  interactions (click / redeem / dismiss) feed      │
│  │ preference │  category weights back into the ranking prompt     │
│  └────────────┘                                                    │
└────────────────────────────────────────────────────────────────────┘
```

**Stack (MVP):** Python 3.12+ · SQLite · httpx (async fetch) · feedparser · FastAPI ·
Anthropic SDK (`claude-opus-4-8`). **Later:** Next.js dashboard, PostgreSQL, Redis
queue, Docker Compose, Telegram bot, browser extension.

Principle: *the simplest architecture that scales naturally*. Everything is a plugin
behind a small interface; swapping SQLite→Postgres or adding notification channels
touches one module each.

### 3.1 Discovery pipeline

- `Source` interface: `name`, `fetch() -> list[RawOpportunity]`. All sources run
  concurrently with per-source error isolation (one dead API never blocks a run).
- MVP sources (no auth, ToS-friendly, public endpoints only):
  - **Hacker News** (Algolia API): Launch/Show HN, "free tier", credits, YC/betas.
  - **Reddit public JSON**: r/developersIndia, r/IndianGaming (deals flair), r/hackathon, r/udemyfreebies.
  - **RSS**: GitHub Education blog, Dev.to (#hackathon/#opensource), Google India blog, curated deal feeds.
- Each source tags candidates with `category` hints and `region` hints; the AI pass
  refines them.
- v2 sources: Devfolio/Unstop (scrape-lite or APIs where offered), Product Hunt API,
  GrabOn/CashKaro India feeds, MeitY/AICTE/Startup India portals, newsletters via IMAP.

### 3.2 AI ranking pipeline

- Batched: up to ~20 opportunities per Claude call (structured-output JSON schema),
  keeping token cost low and enabling cache reuse of the profile preamble.
- Per item Claude estimates: `relevance`, `legitimacy`, `est_value_inr`, `effort_hours`,
  `eligibility` (eligible / likely / unlikely / no), `region_scope` (global/india/state/city),
  `urgency` (+ deadline extraction), `confidence`, one-line `reasoning`.
- Composite score = `relevance × legitimacy × value_density (value/effort) × eligibility
  × urgency_boost × learned_category_weight`, computed in code (deterministic, tunable),
  not by the model.
- No credentials → deterministic keyword heuristic scorer (clearly labeled `scorer=heuristic`).
- Prompt-caching: profile + rubric are the stable prefix with `cache_control`; the batch
  of items is the volatile suffix.

### 3.3 Personalization engine

- `interactions` table records every click / save / redeem / dismiss with timestamp.
- Category weights: exponentially-decayed redeem:dismiss ratio per category →
  multiplier in [0.5, 1.5] applied to composite score and injected into the ranking
  prompt ("user consistently ignores gaming deals; prioritizes AI tools").
- v2: local embeddings (e.g. `bge-small`) for semantic similarity to previously-redeemed
  items; memory graph of brands/subscriptions/stack.

### 3.4 Price & coupon intelligence (v2)

- `price_history` table + per-retailer fetchers (Amazon.in/Flipkart via public pages,
  respecting robots/ToS); fake-discount detection = current price vs 90-day median.
- Indian sale calendar (Great Indian Festival, Big Billion Days, Republic/Independence
  Day, Diwali, EOSS) as a *wait/buy-now* signal in recommendations.
- Coupon verification: headless check of code validity where ToS permits; otherwise
  crowd-sourced freshness (report-back from the user).
- Payment optimizer: given card/UPI/bank set from profile, surface instant-discount and
  cashback combos to minimize final price.

### 3.5 Browser assistant (v3)

- MV3 extension. On Amazon.in/Flipkart product pages: price history sparkline, verdict
  (buy/wait), applicable bank offers, cashback routes (CashKaro deep-link).
- On SaaS pricing pages: student/edu plan detection, GitHub Student Pack matches, free
  alternatives, referral routes.
- Extension only *reads* pages the user is on and calls the local Hermes API — no
  automation of checkout or forms beyond profile autofill.

### 3.6 Notifications (v2)

- Urgency tiers: Critical (real-time push) / High (same-day) / Medium (daily digest) /
  Low (weekly digest). Channel adapters: Telegram bot first (free, trivial), then email,
  Discord webhook, ntfy mobile push. Anti-spam: notify only when `confidence ≥ 0.7` and
  composite score above the user's rolling 80th percentile.

### 3.7 Automation boundaries

Allowed: saving, reminders, deadline tracking, opening application pages, prefilling
reusable profile data, status monitoring. **Never:** mass giveaway entry, CAPTCHA/
verification bypass, rate-limit evasion, or anything against a platform's ToS.

## 4. Database schema (SQLite, v1)

```sql
CREATE TABLE opportunities (
  id            INTEGER PRIMARY KEY,
  fingerprint   TEXT UNIQUE NOT NULL,      -- dedupe key (normalized url|title hash)
  title         TEXT NOT NULL,
  url           TEXT NOT NULL,
  description   TEXT,
  source        TEXT NOT NULL,             -- plugin name
  category      TEXT,                      -- hackathon|cloud_credits|deal|scholarship|...
  region_hint   TEXT,                      -- source-level guess
  posted_at     TEXT,                      -- ISO 8601
  discovered_at TEXT NOT NULL,
  deadline      TEXT,                      -- ISO 8601, AI-extracted
  status        TEXT NOT NULL DEFAULT 'new'  -- new|ranked|notified|redeemed|dismissed|expired
);

CREATE TABLE scores (
  opportunity_id  INTEGER PRIMARY KEY REFERENCES opportunities(id),
  scorer          TEXT NOT NULL,           -- 'claude-opus-4-8' | 'heuristic'
  relevance       REAL, legitimacy REAL, confidence REAL,
  est_value_inr   REAL, effort_hours REAL,
  eligibility     TEXT,                    -- eligible|likely|unlikely|no
  region_scope    TEXT,                    -- global|india|maharashtra|mumbai|other
  urgency         TEXT,                    -- critical|high|medium|low
  composite       REAL NOT NULL,
  reasoning       TEXT,
  scored_at       TEXT NOT NULL
);

CREATE TABLE interactions (            -- learning loop
  id INTEGER PRIMARY KEY,
  opportunity_id INTEGER REFERENCES opportunities(id),
  action TEXT NOT NULL,                -- click|save|redeem|dismiss
  created_at TEXT NOT NULL
);

CREATE TABLE price_history (           -- v2: price intelligence
  id INTEGER PRIMARY KEY,
  product_key TEXT NOT NULL, retailer TEXT NOT NULL,
  price_inr REAL NOT NULL, captured_at TEXT NOT NULL
);
```

Postgres migration is mechanical (same schema, `SERIAL`/`TIMESTAMPTZ`), planned when
multi-user or worker concurrency demands it.

## 5. Roadmap & milestones

| Milestone | Scope | Definition of done |
|---|---|---|
| **M1 — MVP core** *(this repo, now)* | Discovery plugins (HN, Reddit, RSS) → dedupe → SQLite → AI/heuristic ranking → terminal digest + FastAPI dashboard, profile.yaml, feedback commands | `discover → rank → digest` runs end-to-end on a real network; dashboard renders ranked list |
| **M2 — Notify & learn** | Telegram alerts with urgency tiers, daily/weekly digests, category-weight learning live in ranking, scheduler (Task Scheduler/cron) | Zero-touch daily operation; dismissals visibly re-rank |
| **M3 — India commerce intel** | Amazon.in/Flipkart price history, fake-discount detection, sale-calendar signals, bank/UPI offer feeds, payment optimizer | "Buy now vs wait" verdicts with historical evidence |
| **M4 — Deep sources** | Devfolio/Unstop/MLH, Product Hunt, GitHub Student Pack watcher, govt portals (AICTE, Startup India, MeitY), newsletter ingestion | ≥15 sources; coverage audit shows <10% missed-opportunity rate vs manual checking |
| **M5 — Browser assistant** | MV3 extension: price overlay on Amazon.in/Flipkart, student-plan detection on SaaS pricing pages | Extension published (self-install), talks to local API |
| **M6 — Command center** | Next.js dashboard: money saved/earned, credits obtained, deadlines board, opportunity score; Docker Compose; Postgres option | Dashboard replaces FastAPI stub; one-command deploy |
