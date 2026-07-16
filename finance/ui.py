"""Ledger UI — one self-contained page.

Visual identity: "evening ledger" — deep green-charcoal paper, cream ink,
Instrument Serif numerals, hairline double-rules like a bound account book.
Chart palette validated (dataviz six-checks) against surface #131A17:
income #2E9C87 · expense #C25B3F, category bars single-hue teal with direct
value labels, budget over-runs flagged with text + icon, never color alone.
"""

PAGE = r"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ledger</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Public+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{
  --paper:#131A17; --panel:#1A2420; --panel2:#16201C;
  --ink:#EDE7DA; --muted:#97A69E; --hair:#2A3630;
  --in:#2E9C87; --out:#C25B3F; --over:#D64545;
  --serif:"Instrument Serif",serif; --sans:"Public Sans",system-ui,sans-serif;
  --mono:"IBM Plex Mono",monospace;
}
*{box-sizing:border-box;margin:0}
body{background:var(--paper);color:var(--ink);font:14.5px/1.55 var(--sans)}
.wrap{max-width:1060px;margin:0 auto;padding:0 22px 90px}

/* header */
header{display:flex;align-items:baseline;gap:16px;padding:30px 0 16px;
  border-bottom:1px solid var(--hair);position:relative}
header::after{content:"";position:absolute;bottom:-4px;left:0;right:0;height:1px;background:var(--hair)}
.wordmark{font:400 30px/1 var(--serif);letter-spacing:.06em}
.wordmark i{color:var(--in)}
.monthnav{margin-left:auto;display:flex;align-items:center;gap:10px;font:500 13px var(--mono)}
.monthnav button{border:1px solid var(--hair);background:var(--panel);color:var(--ink);
  border-radius:6px;width:30px;height:30px;cursor:pointer;font-size:15px}
.monthnav button:hover{border-color:var(--muted)}
.monthnav button:focus-visible{outline:2px solid var(--in);outline-offset:2px}

/* hero */
.hero{display:grid;grid-template-columns:minmax(0,1.4fr) repeat(3,minmax(0,1fr));
  gap:14px;padding:26px 0;border-bottom:1px solid var(--hair);align-items:end}
.net .lbl{font:500 11px var(--mono);color:var(--muted);text-transform:uppercase;letter-spacing:.12em}
.net .fig{font:400 64px/1.05 var(--serif);letter-spacing:-.01em;margin-top:4px}
.net .fig.neg{color:var(--out)}
.net .fig .pfx{font-size:.55em;vertical-align:.32em;color:var(--muted)}
.tile{background:var(--panel);border:1px solid var(--hair);border-radius:10px;padding:14px 16px}
.tile .lbl{font:500 10.5px var(--mono);color:var(--muted);text-transform:uppercase;letter-spacing:.12em}
.tile .val{font:400 26px/1.2 var(--serif);margin-top:3px}
.tile .val.in{color:var(--in)} .tile .val.out{color:var(--out)}
.tile .sub{font:400 11px var(--mono);color:var(--muted)}

/* sections */
h2{font:400 21px var(--serif);letter-spacing:.02em;margin:30px 0 12px}
.grid2{display:grid;grid-template-columns:1.2fr 1fr;gap:16px;align-items:start}
.panel{background:var(--panel);border:1px solid var(--hair);border-radius:12px;padding:18px}
.panel h3{font:500 11px var(--mono);color:var(--muted);text-transform:uppercase;
  letter-spacing:.12em;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center}
.legend{display:flex;gap:14px;font:400 11px var(--mono);color:var(--muted);text-transform:none;letter-spacing:0}
.legend .sw{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px;vertical-align:-1px}
svg text{font:400 10.5px var(--mono);fill:var(--muted)}
svg .vlabel{fill:var(--ink)}
details.dataview{margin-top:10px;font:400 12px var(--mono);color:var(--muted)}
details.dataview table{width:100%;border-collapse:collapse;margin-top:6px}
details.dataview td,details.dataview th{border-top:1px solid var(--hair);padding:4px 6px;text-align:right}
details.dataview th:first-child,details.dataview td:first-child{text-align:left}

/* tooltip */
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--paper);
  font:500 12px var(--mono);border-radius:6px;padding:6px 9px;z-index:50;display:none;white-space:nowrap}

/* budgets */
.budget{display:flex;align-items:center;gap:12px;padding:10px 0;border-top:1px solid var(--hair)}
.budget:first-of-type{border-top:none}
.budget .cat{width:110px;text-transform:capitalize;font-weight:500}
.budget .bar{flex:1;height:10px;background:var(--panel2);border-radius:5px;overflow:hidden}
.budget .bar i{display:block;height:100%;border-radius:5px;background:var(--in)}
.budget.warn .bar i{background:#C7A23A}
.budget.over .bar i{background:var(--over)}
.budget .nums{font:400 12px var(--mono);color:var(--muted);width:180px;text-align:right}
.budget .flag{font:600 10px var(--mono);color:var(--over)}
.setbudget{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}
.setbudget select,.setbudget input{background:var(--panel2);border:1px solid var(--hair);
  color:var(--ink);border-radius:6px;padding:7px 9px;font:inherit}

/* transactions */
.addrow{display:grid;grid-template-columns:110px 96px 1fr 1fr 130px 130px auto;gap:8px;
  background:var(--panel);border:1px solid var(--hair);border-radius:12px;padding:14px;margin-bottom:14px}
.addrow input,.addrow select{background:var(--panel2);border:1px solid var(--hair);color:var(--ink);
  border-radius:6px;padding:8px 10px;font:inherit;width:100%}
.addrow input:focus,.addrow select:focus,.setbudget input:focus,.setbudget select:focus{outline:2px solid var(--in);outline-offset:1px}
.kindtoggle{display:flex;border:1px solid var(--hair);border-radius:6px;overflow:hidden}
.kindtoggle button{flex:1;border:0;background:var(--panel2);color:var(--muted);font:inherit;padding:8px 0;cursor:pointer}
.kindtoggle button.on.exp{background:var(--out);color:var(--paper);font-weight:600}
.kindtoggle button.on.inc{background:var(--in);color:var(--paper);font-weight:600}
.btn{border:1px solid var(--ink);background:var(--ink);color:var(--paper);border-radius:6px;
  padding:8px 18px;font:600 13.5px var(--sans);cursor:pointer}
.btn:hover{background:transparent;color:var(--ink)}
.txrow{display:flex;align-items:center;gap:12px;padding:11px 4px;border-top:1px solid var(--hair)}
.txrow .d{font:400 11.5px var(--mono);color:var(--muted);width:58px}
.txrow .catchip{font:500 10.5px var(--mono);border:1px solid var(--hair);border-radius:10px;
  padding:2px 9px;text-transform:capitalize;color:var(--muted)}
.txrow .note{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.txrow .m{font:400 10.5px var(--mono);color:var(--muted)}
.txrow .amt{font:500 15px var(--mono);width:110px;text-align:right}
.txrow .amt.in{color:var(--in)} .txrow .amt.out{color:var(--ink)}
.txrow .del{border:none;background:none;color:var(--muted);cursor:pointer;border-radius:4px;padding:2px 7px}
.txrow .del:hover{background:var(--hair);color:var(--ink)}
.empty{padding:36px;text-align:center;color:var(--muted)}
@media (max-width:840px){
  .hero{grid-template-columns:1fr 1fr}.net{grid-column:1/-1}
  .grid2{grid-template-columns:1fr}
  .addrow{grid-template-columns:1fr 1fr}
}
@media (prefers-reduced-motion:no-preference){
  .budget .bar i{transition:width .35s ease}
}
</style></head><body><div class="wrap">

<header>
  <div class="wordmark">LEDGER<i>.</i></div>
  <div class="monthnav">
    <button onclick="shiftMonth(-1)" aria-label="Previous month">‹</button>
    <span id="monthlabel"></span>
    <button onclick="shiftMonth(1)" aria-label="Next month">›</button>
  </div>
</header>

<div class="hero">
  <div class="net">
    <div class="lbl">Net this month</div>
    <div class="fig" id="net"><span class="pfx">₹</span>0</div>
  </div>
  <div class="tile"><div class="lbl">Money in</div><div class="val in" id="tin">₹0</div><div class="sub" id="tin-n"></div></div>
  <div class="tile"><div class="lbl">Money out</div><div class="val out" id="tout">₹0</div><div class="sub" id="tout-n"></div></div>
  <div class="tile"><div class="lbl">Budgets</div><div class="val" id="tbud">—</div><div class="sub" id="tbud-n"></div></div>
</div>

<div class="grid2" style="margin-top:24px">
  <div class="panel">
    <h3>Six-month flow
      <span class="legend"><span><span class="sw" style="background:var(--in)"></span>in</span>
      <span><span class="sw" style="background:var(--out)"></span>out</span></span>
    </h3>
    <div id="trend"></div>
    <details class="dataview"><summary>view data</summary><div id="trendtable"></div></details>
  </div>
  <div class="panel">
    <h3>Where it went</h3>
    <div id="cats"></div>
  </div>
</div>

<h2>Budgets</h2>
<div class="panel">
  <div id="budgets"><div class="empty">No budgets set — add one below.</div></div>
  <form class="setbudget" onsubmit="saveBudget(event)">
    <select id="b-cat"></select>
    <input id="b-limit" type="number" min="1" placeholder="monthly limit ₹" required style="width:150px">
    <button class="btn" type="submit">Set budget</button>
  </form>
</div>

<h2>Transactions</h2>
<form class="addrow" onsubmit="addTx(event)">
  <input id="t-amount" type="number" step="0.01" min="0.01" placeholder="₹ amount" required>
  <div class="kindtoggle">
    <button type="button" id="k-exp" class="on exp" onclick="setKind('expense')">out</button>
    <button type="button" id="k-inc" class="inc" onclick="setKind('income')">in</button>
  </div>
  <select id="t-category"></select>
  <input id="t-note" type="text" placeholder="note (e.g. hostel mess, Zomato)">
  <select id="t-method"></select>
  <input id="t-date" type="date">
  <button class="btn" type="submit">Add</button>
</form>
<div class="panel" id="txlist"><div class="empty">Loading…</div></div>

<div id="tip" role="presentation"></div>

<script>
let META = null;
let month = new Date().toISOString().slice(0, 7);
let kind = "expense";

const inr = v => "₹" + Math.round(v).toLocaleString("en-IN");
const esc = s => (s || "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const monthName = m => new Date(m + "-02").toLocaleDateString("en-IN", { month: "long", year: "numeric" });
const shortMonth = m => new Date(m + "-02").toLocaleDateString("en-IN", { month: "short" });

const tip = document.getElementById("tip");
function showTip(e, text) {
  tip.textContent = text; tip.style.display = "block";
  tip.style.left = Math.min(e.clientX + 12, innerWidth - 170) + "px";
  tip.style.top = (e.clientY - 34) + "px";
}
function hideTip() { tip.style.display = "none"; }

function shiftMonth(d) {
  const [y, m] = month.split("-").map(Number);
  const nd = new Date(y, m - 1 + d, 2);
  month = nd.toISOString().slice(0, 7);
  refresh();
}

function setKind(k) {
  kind = k;
  document.getElementById("k-exp").classList.toggle("on", k === "expense");
  document.getElementById("k-inc").classList.toggle("on", k === "income");
  fillCategories();
}

function fillCategories() {
  const cats = kind === "expense" ? META.expense_categories : META.income_categories;
  document.getElementById("t-category").innerHTML =
    cats.map(c => `<option value="${c}">${c}</option>`).join("");
}

/* ── charts (hand-rolled SVG, palette pre-validated) ── */

function trendChart(trend) {
  const W = 520, H = 210, P = { l: 8, r: 8, t: 14, b: 24 };
  const max = Math.max(1, ...trend.flatMap(t => [t.income, t.expense]));
  const iw = (W - P.l - P.r) / trend.length;
  const bw = Math.min(22, iw / 2 - 6);
  const y = v => P.t + (H - P.t - P.b) * (1 - v / max);
  let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Income vs expense, last six months">`;
  s += `<line x1="${P.l}" y1="${H - P.b}" x2="${W - P.r}" y2="${H - P.b}" stroke="var(--hair)"/>`;
  trend.forEach((t, i) => {
    const cx = P.l + iw * i + iw / 2;
    [["income", t.income, "var(--in)", cx - bw - 1.5], ["expense", t.expense, "var(--out)", cx + 1.5]].forEach(([k, v, color, x]) => {
      const h = Math.max(v > 0 ? 3 : 0, H - P.b - y(v));
      s += `<rect x="${x}" y="${H - P.b - h}" width="${bw}" height="${h}" rx="3" fill="${color}"
             data-tip="${shortMonth(t.month)} ${k === "income" ? "in" : "out"}: ${inr(v)}"/>`;
    });
    s += `<text x="${cx}" y="${H - 7}" text-anchor="middle">${shortMonth(t.month)}</text>`;
  });
  s += "</svg>";
  document.getElementById("trend").innerHTML = s;
  document.getElementById("trendtable").innerHTML =
    `<table><tr><th>month</th><th>in</th><th>out</th><th>net</th></tr>` +
    trend.map(t => `<tr><td>${shortMonth(t.month)}</td><td>${inr(t.income)}</td><td>${inr(t.expense)}</td><td>${inr(t.net)}</td></tr>`).join("") + "</table>";
  document.querySelectorAll("#trend rect").forEach(r => {
    r.addEventListener("mousemove", e => showTip(e, r.dataset.tip));
    r.addEventListener("mouseleave", hideTip);
  });
}

function catChart(cats, total) {
  const el = document.getElementById("cats");
  if (!cats.length) { el.innerHTML = `<div class="empty">No spending recorded this month.</div>`; return; }
  const shown = cats.slice(0, 7);
  const rest = cats.slice(7);
  if (rest.length) shown.push({ category: "everything else", total: rest.reduce((a, c) => a + c.total, 0), n: rest.reduce((a, c) => a + c.n, 0) });
  const max = shown[0].total;
  const W = 400, RH = 34;
  let s = `<svg viewBox="0 0 ${W} ${shown.length * RH}" width="100%" role="img" aria-label="Spending by category">`;
  shown.forEach((c, i) => {
    const w = Math.max(3, (c.total / max) * (W - 150));
    const yy = i * RH;
    s += `<text x="0" y="${yy + 21}" style="text-transform:capitalize">${esc(c.category)}</text>
          <rect x="118" y="${yy + 10}" width="${w}" height="15" rx="3" fill="var(--in)"
            data-tip="${esc(c.category)}: ${inr(c.total)} · ${c.n} txn · ${(c.total / total * 100).toFixed(0)}%"/>
          <text class="vlabel" x="${122 + w}" y="${yy + 22}">${inr(c.total)}</text>`;
  });
  s += "</svg>";
  el.innerHTML = s;
  document.querySelectorAll("#cats rect").forEach(r => {
    r.addEventListener("mousemove", e => showTip(e, r.dataset.tip));
    r.addEventListener("mouseleave", hideTip);
  });
}

/* ── data ── */

async function refresh() {
  document.getElementById("monthlabel").textContent = monthName(month);
  const [s, txs] = await Promise.all([
    (await fetch(`/api/summary?month=${month}`)).json(),
    (await fetch(`/api/transactions?month=${month}`)).json(),
  ]);
  const t = s.totals;
  const net = document.getElementById("net");
  net.innerHTML = `<span class="pfx">₹</span>${Math.abs(Math.round(t.net)).toLocaleString("en-IN")}${t.net < 0 ? " dr" : ""}`;
  net.classList.toggle("neg", t.net < 0);
  document.getElementById("tin").textContent = inr(t.income);
  document.getElementById("tout").textContent = inr(t.expense);
  const inN = txs.filter(x => x.kind === "income").length, outN = txs.filter(x => x.kind === "expense").length;
  document.getElementById("tin-n").textContent = inN ? `${inN} entries` : "";
  document.getElementById("tout-n").textContent = outN ? `${outN} entries` : "";

  const over = s.budgets.filter(b => b.spent > b.limit).length;
  document.getElementById("tbud").textContent = s.budgets.length ? (over ? `${over} over` : "on track") : "—";
  document.getElementById("tbud-n").textContent = s.budgets.length ? `${s.budgets.length} set` : "none set";

  trendChart(s.trend);
  catChart(s.by_category, t.expense || 1);

  document.getElementById("budgets").innerHTML = s.budgets.length ? s.budgets.map(b => {
    const pct = Math.min(100, b.spent / b.limit * 100);
    const cls = b.spent > b.limit ? "over" : pct > 80 ? "warn" : "";
    return `<div class="budget ${cls}">
      <span class="cat">${esc(b.category)}</span>
      <div class="bar"><i style="width:${pct}%"></i></div>
      <span class="nums">${inr(b.spent)} / ${inr(b.limit)}
        ${b.spent > b.limit ? `<span class="flag">▲ OVER by ${inr(b.spent - b.limit)}</span>` : ""}</span>
    </div>`;
  }).join("") : `<div class="empty">No budgets set — add one below.</div>`;

  document.getElementById("txlist").innerHTML = txs.length ? txs.map(x => `
    <div class="txrow">
      <span class="d">${x.occurred_on.slice(8)} ${shortMonth(x.occurred_on.slice(0, 7))}</span>
      <span class="catchip">${esc(x.category)}</span>
      <span class="note">${esc(x.note) || '<span style="color:var(--muted)">—</span>'}</span>
      <span class="m">${esc(x.method)}</span>
      <span class="amt ${x.kind === "income" ? "in" : "out"}">${x.kind === "income" ? "+" : "−"}${inr(x.amount)}</span>
      <button class="del" title="Delete" onclick="delTx(${x.id})">✕</button>
    </div>`).join("") : `<div class="empty">Nothing recorded for ${monthName(month)} — add your first entry above.</div>`;
}

async function addTx(e) {
  e.preventDefault();
  const body = {
    amount: parseFloat(document.getElementById("t-amount").value),
    kind,
    category: document.getElementById("t-category").value,
    note: document.getElementById("t-note").value,
    method: document.getElementById("t-method").value,
    occurred_on: document.getElementById("t-date").value || META.today,
  };
  const r = await fetch("/api/transactions", { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (r.ok) {
    document.getElementById("t-amount").value = "";
    document.getElementById("t-note").value = "";
    document.getElementById("t-amount").focus();
    month = body.occurred_on.slice(0, 7);
    refresh();
  }
}

async function delTx(id) {
  await fetch(`/api/transactions/${id}`, { method: "DELETE" });
  refresh();
}

async function saveBudget(e) {
  e.preventDefault();
  await fetch("/api/budgets", { method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category: document.getElementById("b-cat").value,
                           monthly_limit: parseFloat(document.getElementById("b-limit").value) }) });
  document.getElementById("b-limit").value = "";
  refresh();
}

(async () => {
  META = await (await fetch("/api/meta")).json();
  fillCategories();
  document.getElementById("t-method").innerHTML = META.methods.map(m => `<option>${m}</option>`).join("");
  document.getElementById("b-cat").innerHTML = META.expense_categories.map(c => `<option>${c}</option>`).join("");
  document.getElementById("t-date").value = META.today;
  refresh();
})();
</script>
</div></body></html>"""
