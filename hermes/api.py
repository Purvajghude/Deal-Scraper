"""FastAPI server: category-wise freebie dashboard + self-refreshing discovery.

The server owns the schedule — a background task re-runs discovery every
REFRESH_HOURS so the board stays fresh with zero manual steps. No AI, no
notifications: just neatly arranged data.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from . import db
from .categorize import CATEGORIES

REFRESH_HOURS = 6

_refresh_state = {"running": False, "last_run": None, "last_new": 0, "last_errors": {}}
_refresh_lock = asyncio.Lock()


async def _run_refresh() -> None:
    from .sources import discover_all

    if _refresh_lock.locked():
        return
    async with _refresh_lock:
        _refresh_state["running"] = True
        try:
            opps, errors = await discover_all()
            con = db.connect()
            try:
                inserted = db.insert_opportunities(con, opps)
            finally:
                con.close()
            _refresh_state["last_new"] = inserted
            _refresh_state["last_errors"] = errors
            _refresh_state["last_run"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        finally:
            _refresh_state["running"] = False


async def _refresh_loop() -> None:
    while True:
        try:
            await _run_refresh()
        except Exception as e:  # keep the loop alive no matter what
            _refresh_state["last_errors"] = {"refresh_loop": repr(e)}
            _refresh_state["running"] = False
        await asyncio.sleep(REFRESH_HOURS * 3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_refresh_loop())
    yield
    task.cancel()


app = FastAPI(title="Hermes", version="0.2.0", lifespan=lifespan)


@app.get("/api/categories")
def api_categories():
    con = db.connect()
    try:
        counts = db.category_counts(con)
    finally:
        con.close()
    return [
        {"slug": slug, "name": name, "emoji": emoji, "count": counts.get(slug, 0)}
        for slug, (name, emoji) in CATEGORIES.items()
    ]


@app.get("/api/opportunities")
def api_opportunities(category: str | None = None, q: str | None = None, limit: int = 300):
    con = db.connect()
    try:
        return [dict(r) for r in db.list_active(con, category, q, limit)]
    finally:
        con.close()


@app.post("/api/opportunities/{opp_id}/{action}")
def api_mark(opp_id: int, action: str):
    if action not in ("click", "save", "redeemed", "dismissed"):
        return {"ok": False, "error": "unknown action"}
    con = db.connect()
    try:
        db.record_interaction(con, opp_id, action)
        return {"ok": True}
    finally:
        con.close()


@app.post("/api/refresh")
async def api_refresh():
    if _refresh_state["running"]:
        return {"started": False, "reason": "already running"}
    asyncio.create_task(_run_refresh())
    return {"started": True}


@app.get("/api/status")
def api_status():
    con = db.connect()
    try:
        day_ago = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="seconds")
        total = con.execute(
            "SELECT COUNT(*) c FROM opportunities WHERE status NOT IN ('dismissed','expired')"
        ).fetchone()["c"]
        return {
            "total": total,
            "new_24h": db.new_since(con, day_ago),
            "refresh": _refresh_state,
        }
    finally:
        con.close()


PAGE = r"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hermes — Freebie Register</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;800;900&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{
  --paper:#F3F5F0; --surface:#FFFFFF; --ink:#1C2733; --muted:#5C6B7A;
  --rule:#DCE2D6; --accent:#D4452B;
  --c-ai_freebies:#6D4FC1; --c-student_offers:#1878B8; --c-govt_schemes:#C07A0E;
  --c-deals_shopping:#C13A5F; --c-food_dining:#BC5215; --c-free_courses:#2D8A5C;
  --c-hackathons:#128A84; --c-dev_programs:#5A6B3B; --c-beta_early_access:#8B4E97;
  --c-other:#5C6B7A;
}
*{box-sizing:border-box;margin:0}
body{background:var(--paper);color:var(--ink);font:15px/1.5 "IBM Plex Sans",system-ui,sans-serif}
a{color:inherit}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px 80px}

/* masthead */
header{border-bottom:3px solid var(--ink);padding:26px 0 14px;margin-bottom:0}
.mast{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px 18px}
.mast h1{font:900 34px/1 "Archivo",sans-serif;letter-spacing:-.5px;text-transform:uppercase}
.mast .sub{font:500 12px "IBM Plex Mono",monospace;color:var(--muted);letter-spacing:.4px}
.mast .newchip{margin-left:auto;font:600 12px "IBM Plex Mono",monospace;color:#fff;
  background:var(--accent);border-radius:3px;padding:4px 9px}
.toolbar{display:flex;gap:10px;margin:14px 0 0;flex-wrap:wrap}
.toolbar input{flex:1;min-width:220px;border:1.5px solid var(--rule);border-radius:6px;
  padding:9px 12px;font:inherit;background:var(--surface);color:var(--ink)}
.toolbar input:focus{outline:2px solid var(--ink);outline-offset:1px}
.toolbar button{border:1.5px solid var(--ink);background:var(--surface);color:var(--ink);
  border-radius:6px;padding:9px 16px;font:600 14px "Archivo",sans-serif;cursor:pointer}
.toolbar button:hover{background:var(--ink);color:#fff}
.toolbar button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.toolbar button[disabled]{opacity:.5;cursor:wait}

/* file-tab category rail */
nav{position:sticky;top:0;background:var(--paper);z-index:5;
  display:flex;gap:6px;overflow-x:auto;padding:14px 0 0;border-bottom:1.5px solid var(--ink)}
nav::-webkit-scrollbar{display:none}
.tab{flex-shrink:0;border:1.5px solid var(--rule);border-bottom:none;background:var(--surface);
  border-radius:8px 8px 0 0;padding:7px 13px 8px;font:600 13px "Archivo",sans-serif;cursor:pointer;
  border-top:3px solid var(--tabc,var(--muted));color:var(--muted);display:flex;gap:7px;align-items:center}
.tab .n{font:500 11px "IBM Plex Mono",monospace;background:var(--paper);border-radius:8px;padding:1px 7px}
.tab.active{color:var(--ink);border-color:var(--ink);border-top:3px solid var(--tabc,var(--ink));
  position:relative}
.tab.active::after{content:"";position:absolute;left:0;right:0;bottom:-2px;height:3px;background:var(--surface)}
.tab:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}

/* register rows */
#list{background:var(--surface);border:1.5px solid var(--ink);border-top:none}
.row{display:flex;gap:14px;padding:13px 16px 13px 12px;border-bottom:1px solid var(--rule);
  border-left:5px solid var(--catc,var(--muted));align-items:flex-start}
.row:last-child{border-bottom:none}
.row:hover{background:#FAFBF8}
.row .body{flex:1;min-width:0}
.row .title{font-weight:600;text-decoration:none}
.row .title:hover{text-decoration:underline;text-underline-offset:3px}
.row .desc{color:var(--muted);font-size:13.5px;margin-top:2px;overflow:hidden;display:-webkit-box;
  -webkit-line-clamp:2;-webkit-box-orient:vertical}
.row .meta{font:400 11.5px "IBM Plex Mono",monospace;color:var(--muted);margin-top:5px;
  display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.badge-new{color:#fff;background:var(--accent);border-radius:3px;padding:1px 6px;font-weight:500}
.catlabel{color:var(--catc,var(--muted));font-weight:500}
.row .x{border:none;background:none;color:var(--muted);cursor:pointer;font-size:15px;
  padding:2px 6px;border-radius:4px;line-height:1}
.row .x:hover{background:var(--rule);color:var(--ink)}
.empty{padding:48px 20px;text-align:center;color:var(--muted);font-size:14px}
.count-line{font:500 11.5px "IBM Plex Mono",monospace;color:var(--muted);padding:10px 2px}
@media (prefers-reduced-motion:no-preference){
  .row{transition:background .12s}
  .tab{transition:color .12s,border-color .12s}
}
@media (max-width:640px){
  .mast h1{font-size:26px}
  .row{padding:12px 12px 12px 10px}
}
</style></head><body><div class="wrap">

<header>
  <div class="mast">
    <h1>Hermes</h1>
    <span class="sub" id="subline">FREEBIE REGISTER</span>
    <span class="newchip" id="newchip" hidden></span>
  </div>
  <div class="toolbar">
    <input id="q" type="search" placeholder="Search everything… (e.g. claude, laptop, scholarship, mcdonald)" aria-label="Search opportunities">
    <button id="refreshBtn" onclick="doRefresh()">Refresh sources</button>
  </div>
</header>

<nav id="tabs" aria-label="Categories"></nav>
<div class="count-line" id="countline"></div>
<div id="list"><div class="empty">Loading the register…</div></div>

<script>
const state = { category: "", q: "" };
let CATS = [];

const catColor = slug => `var(--c-${slug}, var(--muted))`;
const fmtDate = iso => {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(d) ? "" : d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
};
const isNew = iso => iso && (Date.now() - new Date(iso).getTime()) < 36 * 3600 * 1000;
const esc = s => (s || "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function loadStatus() {
  const s = await (await fetch("/api/status")).json();
  document.getElementById("subline").textContent =
    `FREEBIE REGISTER · ${new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })} · ${s.total} live`;
  const chip = document.getElementById("newchip");
  if (s.new_24h > 0) { chip.hidden = false; chip.textContent = `${s.new_24h} new in 24h`; }
  return s;
}

async function loadTabs() {
  CATS = await (await fetch("/api/categories")).json();
  const total = CATS.reduce((a, c) => a + c.count, 0);
  const tabs = [{ slug: "", name: "All", emoji: "🗂️", count: total }, ...CATS.filter(c => c.count > 0)];
  document.getElementById("tabs").innerHTML = tabs.map(c => `
    <button class="tab ${state.category === c.slug ? "active" : ""}" style="--tabc:${c.slug ? catColor(c.slug) : "var(--ink)"}"
      onclick="setCat('${c.slug}')">${c.emoji} ${esc(c.name)} <span class="n">${c.count}</span></button>`).join("");
}

async function loadList() {
  const params = new URLSearchParams();
  if (state.category) params.set("category", state.category);
  if (state.q) params.set("q", state.q);
  const items = await (await fetch(`/api/opportunities?${params}`)).json();
  const catName = Object.fromEntries(CATS.map(c => [c.slug, c.name]));
  document.getElementById("countline").textContent =
    `${items.length} entries${state.q ? ` matching “${state.q}”` : ""}${state.category ? ` · ${catName[state.category] || state.category}` : " · all categories"}`;
  document.getElementById("list").innerHTML = items.length ? items.map(o => `
    <div class="row" style="--catc:${catColor(o.category)}" id="row-${o.id}">
      <div class="body">
        <a class="title" href="${esc(o.url)}" target="_blank" rel="noopener"
           onclick="fetch('/api/opportunities/${o.id}/click',{method:'POST'})">${esc(o.title)}</a>
        ${o.description && !o.title.includes(o.description.slice(0, 60)) ? `<div class="desc">${esc(o.description.replace(/<[^>]+>/g, ""))}</div>` : ""}
        <div class="meta">
          ${isNew(o.discovered_at) ? '<span class="badge-new">NEW</span>' : ""}
          <span class="catlabel">${esc(catName[o.category] || o.category)}</span>
          <span>via ${esc(o.source)}</span>
          ${fmtDate(o.posted_at || o.discovered_at) ? `<span>${fmtDate(o.posted_at || o.discovered_at)}</span>` : ""}
          ${o.region_hint === "india" ? "<span>🇮🇳 India</span>" : ""}
        </div>
      </div>
      <button class="x" title="Dismiss — hide this forever" onclick="dismiss(${o.id})">✕</button>
    </div>`).join("")
    : `<div class="empty">Nothing here${state.q ? " for this search" : " yet"}. Hit “Refresh sources” to pull the latest.</div>`;
}

function setCat(slug) { state.category = slug; loadTabs(); loadList(); }

async function dismiss(id) {
  await fetch(`/api/opportunities/${id}/dismissed`, { method: "POST" });
  document.getElementById(`row-${id}`)?.remove();
  loadTabs();
}

let qTimer;
document.getElementById("q").addEventListener("input", e => {
  clearTimeout(qTimer);
  qTimer = setTimeout(() => { state.q = e.target.value.trim(); loadList(); }, 250);
});

async function doRefresh() {
  const btn = document.getElementById("refreshBtn");
  btn.disabled = true; btn.textContent = "Refreshing…";
  await fetch("/api/refresh", { method: "POST" });
  const poll = setInterval(async () => {
    const s = await (await fetch("/api/status")).json();
    if (!s.refresh.running) {
      clearInterval(poll);
      btn.disabled = false; btn.textContent = "Refresh sources";
      await Promise.all([loadStatus(), loadTabs(), loadList()]);
    }
  }, 1500);
}

(async () => { await loadStatus(); await loadTabs(); await loadList(); })();
</script>
</div></body></html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return PAGE
