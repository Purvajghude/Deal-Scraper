"""Command-center dashboard (single self-contained page served at /)."""

PAGE = r"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hermes — Freebie Register</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;800;900&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{
  --paper:#F3F5F0; --surface:#FFFFFF; --ink:#1C2733; --muted:#5C6B7A;
  --rule:#DCE2D6; --accent:#D4452B; --good:#2D8A5C;
  --c-ai_freebies:#6D4FC1; --c-student_offers:#1878B8; --c-govt_schemes:#C07A0E;
  --c-deals_shopping:#C13A5F; --c-food_dining:#BC5215; --c-free_courses:#2D8A5C;
  --c-hackathons:#128A84; --c-dev_programs:#5A6B3B; --c-beta_early_access:#8B4E97;
  --c-other:#5C6B7A;
}
*{box-sizing:border-box;margin:0}
body{background:var(--paper);color:var(--ink);font:15px/1.5 "IBM Plex Sans",system-ui,sans-serif}
a{color:inherit}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px 80px}

header{border-bottom:3px solid var(--ink);padding:26px 0 14px}
.mast{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px 18px}
.mast h1{font:900 34px/1 "Archivo",sans-serif;letter-spacing:-.5px;text-transform:uppercase}
.mast .sub{font:500 12px "IBM Plex Mono",monospace;color:var(--muted);letter-spacing:.4px}
.mast .newchip{margin-left:auto;font:600 12px "IBM Plex Mono",monospace;color:#fff;
  background:var(--accent);border-radius:3px;padding:4px 9px}

.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:16px 0 0}
.stat{background:var(--surface);border:1.5px solid var(--rule);border-radius:8px;padding:10px 14px}
.stat b{font:800 22px/1.1 "Archivo",sans-serif;display:block}
.stat span{font:500 10.5px "IBM Plex Mono",monospace;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.stat.alert{border-color:var(--good)} .stat.alert b{color:var(--good)}

.toolbar{display:flex;gap:10px;margin:14px 0 0;flex-wrap:wrap;align-items:center}
.toolbar input[type=search]{flex:1;min-width:220px;border:1.5px solid var(--rule);border-radius:6px;
  padding:9px 12px;font:inherit;background:var(--surface);color:var(--ink)}
.toolbar input:focus{outline:2px solid var(--ink);outline-offset:1px}
.btn{border:1.5px solid var(--ink);background:var(--surface);color:var(--ink);
  border-radius:6px;padding:9px 16px;font:600 14px "Archivo",sans-serif;cursor:pointer}
.btn:hover{background:var(--ink);color:#fff}
.btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.btn[disabled]{opacity:.5;cursor:wait}
.sortwrap{font:500 12px "IBM Plex Mono",monospace;color:var(--muted);display:flex;gap:6px;align-items:center}
.sortwrap button{border:1.5px solid var(--rule);background:var(--surface);border-radius:5px;
  padding:5px 10px;font:inherit;color:var(--muted);cursor:pointer}
.sortwrap button.on{border-color:var(--ink);color:var(--ink);font-weight:600}

nav{position:sticky;top:0;background:var(--paper);z-index:5;
  display:flex;gap:6px;overflow-x:auto;padding:14px 0 0;border-bottom:1.5px solid var(--ink)}
nav::-webkit-scrollbar{display:none}
.tab{flex-shrink:0;border:1.5px solid var(--rule);border-bottom:none;background:var(--surface);
  border-radius:8px 8px 0 0;padding:7px 13px 8px;font:600 13px "Archivo",sans-serif;cursor:pointer;
  border-top:3px solid var(--tabc,var(--muted));color:var(--muted);display:flex;gap:7px;align-items:center}
.tab .n{font:500 11px "IBM Plex Mono",monospace;background:var(--paper);border-radius:8px;padding:1px 7px}
.tab.active{color:var(--ink);border-color:var(--ink);position:relative}
.tab.active::after{content:"";position:absolute;left:0;right:0;bottom:-2px;height:3px;background:var(--surface)}
.tab:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}

#list,#watchpanel{background:var(--surface);border:1.5px solid var(--ink);border-top:none}
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
.badge-score{color:#fff;background:var(--ink);border-radius:3px;padding:1px 6px;font-weight:500}
.catlabel{color:var(--catc,var(--muted));font-weight:500}
.rowbtns{display:flex;flex-direction:column;gap:4px}
.row .x,.row .ok{border:none;background:none;color:var(--muted);cursor:pointer;font-size:14px;
  padding:2px 6px;border-radius:4px;line-height:1.2}
.row .x:hover{background:var(--rule);color:var(--ink)}
.row .ok:hover{background:var(--good);color:#fff}
.empty{padding:48px 20px;text-align:center;color:var(--muted);font-size:14px}
.count-line{font:500 11.5px "IBM Plex Mono",monospace;color:var(--muted);padding:10px 2px}

/* price watch */
.addwatch{display:flex;gap:8px;flex-wrap:wrap;padding:14px 16px;border-bottom:1px solid var(--rule)}
.addwatch input{border:1.5px solid var(--rule);border-radius:6px;padding:8px 10px;font:inherit;background:var(--paper)}
.addwatch input:focus{outline:2px solid var(--ink)}
.addwatch .u{flex:2;min-width:200px}.addwatch .l{flex:1;min-width:120px}.addwatch .t{width:110px}
.witem{display:flex;gap:14px;align-items:center;padding:13px 16px;border-bottom:1px solid var(--rule)}
.witem:last-child{border-bottom:none}
.witem .info{flex:1;min-width:0}
.witem .price{font:800 20px "Archivo",sans-serif}
.witem .vd{font:500 11px "IBM Plex Mono",monospace;border-radius:3px;padding:2px 7px;color:#fff;background:var(--muted)}
.vd.BUY{background:var(--good)}.vd.GOOD{background:#4a7d43}.vd.WAIT{background:var(--accent)}
.witem svg{flex-shrink:0}
@media (prefers-reduced-motion:no-preference){.row{transition:background .12s}}
@media (max-width:640px){.mast h1{font-size:26px}.row{padding:12px 12px 12px 10px}}
</style></head><body><div class="wrap">

<header>
  <div class="mast">
    <h1>Hermes</h1>
    <span class="sub" id="subline">FREEBIE REGISTER</span>
    <span class="newchip" id="newchip" hidden></span>
  </div>
  <div class="stats" id="stats"></div>
  <div class="toolbar">
    <input id="q" type="search" placeholder="Search everything… (e.g. claude, laptop, scholarship, mcdonald)" aria-label="Search opportunities">
    <span class="sortwrap">sort
      <button id="sort-new" class="on" onclick="setSort('new')">latest</button>
      <button id="sort-smart" onclick="setSort('smart')" title="AI score when available">smart</button>
    </span>
    <button class="btn" id="refreshBtn" onclick="doRefresh()">Refresh</button>
  </div>
</header>

<nav id="tabs" aria-label="Categories"></nav>
<div class="count-line" id="countline"></div>
<div id="watchpanel" hidden>
  <form class="addwatch" onsubmit="addWatch(event)">
    <input class="u" id="w-url" type="url" required placeholder="Product URL (amazon.in, flipkart…)">
    <input class="l" id="w-label" type="text" required placeholder="Name it (e.g. Sony XM5)">
    <input class="t" id="w-target" type="number" min="1" placeholder="₹ target">
    <button class="btn" type="submit">Watch</button>
  </form>
  <div id="watchlist"></div>
</div>
<div id="list"><div class="empty">Loading the register…</div></div>

<script>
const state = { category: "", q: "", sort: "new", view: "register" };
let CATS = [];

const catColor = s => `var(--c-${s}, var(--muted))`;
const inr = v => "₹" + Math.round(v).toLocaleString("en-IN");
const fmtDate = iso => { if (!iso) return ""; const d = new Date(iso); return isNaN(d) ? "" : d.toLocaleDateString("en-IN", { day: "numeric", month: "short" }); };
const isNew = iso => iso && (Date.now() - new Date(iso).getTime()) < 36 * 3600 * 1000;
const esc = s => (s || "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function loadStatus() {
  const s = await (await fetch("/api/status")).json();
  document.getElementById("subline").textContent =
    `FREEBIE REGISTER · ${new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}`;
  const chip = document.getElementById("newchip");
  if (s.new_24h > 0) { chip.hidden = false; chip.textContent = `${s.new_24h} new in 24h`; }
  const scorer = s.refresh.last_scorer || "—";
  const wl = await (await fetch("/api/watchlist")).json();
  const buys = wl.filter(w => w.verdict === "BUY").length;
  document.getElementById("stats").innerHTML = `
    <div class="stat"><b>${s.total}</b><span>live opportunities</span></div>
    <div class="stat"><b>${s.new_24h}</b><span>new in 24h</span></div>
    <div class="stat"><b>${s.ranked}</b><span>ranked · ${esc(scorer.replace("claude-", ""))}</span></div>
    <div class="stat ${buys ? "alert" : ""}"><b>${buys ? buys + " BUY" : wl.length}</b><span>${buys ? "price alerts!" : "products watched"}</span></div>
    <div class="stat"><b>${inr(s.value_realized_inr || 0)}</b><span>value realized</span></div>`;
  return s;
}

async function loadTabs() {
  CATS = await (await fetch("/api/categories")).json();
  const total = CATS.reduce((a, c) => a + c.count, 0);
  const tabs = [{ slug: "", name: "All", emoji: "🗂️", count: total },
                ...CATS.filter(c => c.count > 0)];
  let html = tabs.map(c => `
    <button class="tab ${state.view === "register" && state.category === c.slug ? "active" : ""}"
      style="--tabc:${c.slug ? catColor(c.slug) : "var(--ink)"}"
      onclick="setCat('${c.slug}')">${c.emoji} ${esc(c.name)} <span class="n">${c.count}</span></button>`).join("");
  html += `<button class="tab ${state.view === "watch" ? "active" : ""}" style="--tabc:var(--good)"
      onclick="setView('watch')">📈 Price watch</button>`;
  document.getElementById("tabs").innerHTML = html;
}

async function loadList() {
  const params = new URLSearchParams();
  if (state.category) params.set("category", state.category);
  if (state.q) params.set("q", state.q);
  params.set("sort", state.sort);
  const items = await (await fetch(`/api/opportunities?${params}`)).json();
  const catName = Object.fromEntries(CATS.map(c => [c.slug, c.name]));
  document.getElementById("countline").textContent =
    `${items.length} entries${state.q ? ` matching “${state.q}”` : ""}${state.category ? ` · ${catName[state.category] || state.category}` : " · all categories"}${state.sort === "smart" ? " · smart order" : ""}`;
  document.getElementById("list").innerHTML = items.length ? items.map(o => `
    <div class="row" style="--catc:${catColor(o.category)}" id="row-${o.id}">
      <div class="body">
        <a class="title" href="${esc(o.url)}" target="_blank" rel="noopener"
           onclick="fetch('/api/opportunities/${o.id}/click',{method:'POST'})">${esc(o.title)}</a>
        ${o.description && !o.title.includes(o.description.slice(0, 60)) ? `<div class="desc">${esc(o.description.replace(/<[^>]+>/g, ""))}</div>` : ""}
        <div class="meta">
          ${isNew(o.discovered_at) ? '<span class="badge-new">NEW</span>' : ""}
          ${state.sort === "smart" && o.composite ? `<span class="badge-score">${Number(o.composite).toFixed(2)}</span>` : ""}
          <span class="catlabel">${esc(catName[o.category] || o.category)}</span>
          <span>via ${esc(o.source)}</span>
          ${fmtDate(o.posted_at || o.discovered_at) ? `<span>${fmtDate(o.posted_at || o.discovered_at)}</span>` : ""}
          ${o.region_hint === "india" ? "<span>🇮🇳 India</span>" : ""}
        </div>
      </div>
      <div class="rowbtns">
        <button class="x" title="Dismiss forever" onclick="mark(${o.id},'dismissed')">✕</button>
        <button class="ok" title="I claimed this!" onclick="mark(${o.id},'redeemed')">✓</button>
      </div>
    </div>`).join("")
    : `<div class="empty">Nothing here${state.q ? " for this search" : " yet"}. Hit “Refresh” to pull the latest.</div>`;
}

function spark(hist) {
  if (!hist || hist.length < 2) return "";
  const vals = hist.map(h => h.price_inr);
  const min = Math.min(...vals), max = Math.max(...vals), range = (max - min) || 1;
  const W = 120, H = 30;
  const pts = vals.map((v, i) => `${(i / (vals.length - 1)) * W},${H - 4 - ((v - min) / range) * (H - 8)}`).join(" ");
  return `<svg width="${W}" height="${H}" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="var(--ink)" stroke-width="1.5"/></svg>`;
}

async function loadWatch() {
  const wl = await (await fetch("/api/watchlist")).json();
  document.getElementById("watchlist").innerHTML = wl.length ? wl.map(w => `
    <div class="witem">
      <div class="info">
        <a class="title" href="${esc(w.url)}" target="_blank" rel="noopener">${esc(w.label)}</a>
        <div class="meta" style="font:400 11.5px 'IBM Plex Mono',monospace;color:var(--muted)">
          ${esc(w.detail)}${w.target_price ? ` · target ${inr(w.target_price)}` : ""} · ${w.history.length} readings</div>
      </div>
      ${spark(w.history)}
      <span class="price">${w.current ? inr(w.current) : "—"}</span>
      <span class="vd ${esc(w.verdict)}">${esc(w.verdict)}</span>
      <button class="x" title="Stop watching" onclick="delWatch(${w.id})">✕</button>
    </div>`).join("")
    : `<div class="empty">Paste a product URL above — Hermes records its price every refresh cycle and tells you when it's genuinely cheap.</div>`;
}

async function addWatch(e) {
  e.preventDefault();
  const body = { url: document.getElementById("w-url").value,
                 label: document.getElementById("w-label").value,
                 target_price: parseFloat(document.getElementById("w-target").value) || null };
  const r = await (await fetch("/api/watchlist", { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })).json();
  if (r.ok) { e.target.reset(); loadWatch(); loadStatus(); }
  else alert(r.error || "could not add");
}

async function delWatch(id) {
  await fetch(`/api/watchlist/${id}`, { method: "DELETE" });
  loadWatch(); loadStatus();
}

function setView(v) {
  state.view = v;
  document.getElementById("watchpanel").hidden = v !== "watch";
  document.getElementById("list").style.display = v === "watch" ? "none" : "";
  document.getElementById("countline").style.display = v === "watch" ? "none" : "";
  loadTabs();
  if (v === "watch") loadWatch();
}

function setCat(slug) { state.view = "register"; state.category = slug; setView("register"); loadList(); }
function setSort(s) {
  state.sort = s;
  document.getElementById("sort-new").classList.toggle("on", s === "new");
  document.getElementById("sort-smart").classList.toggle("on", s === "smart");
  loadList();
}

async function mark(id, action) {
  await fetch(`/api/opportunities/${id}/${action}`, { method: "POST" });
  document.getElementById(`row-${id}`)?.remove();
  loadTabs(); if (action === "redeemed") loadStatus();
}

let qTimer;
document.getElementById("q").addEventListener("input", e => {
  clearTimeout(qTimer);
  qTimer = setTimeout(() => { state.q = e.target.value.trim(); if (state.view !== "register") setView("register"); loadList(); }, 250);
});

async function doRefresh() {
  const btn = document.getElementById("refreshBtn");
  btn.disabled = true;
  await fetch("/api/refresh", { method: "POST" });
  const poll = setInterval(async () => {
    const s = await (await fetch("/api/status")).json();
    btn.textContent = s.refresh.running ? (s.refresh.stage || "working") + "…" : "Refresh";
    if (!s.refresh.running) {
      clearInterval(poll); btn.disabled = false;
      await Promise.all([loadStatus(), loadTabs(), state.view === "watch" ? loadWatch() : loadList()]);
    }
  }, 1500);
}

(async () => { await loadStatus(); await loadTabs(); await loadList(); })();
</script>
</div></body></html>"""
