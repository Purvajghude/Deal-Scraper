const out = document.getElementById("out");
const esc = s => s.replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
let timer;

document.getElementById("q").addEventListener("input", e => {
  clearTimeout(timer);
  timer = setTimeout(() => search(e.target.value.trim()), 250);
});

async function search(q) {
  if (!q) { out.innerHTML = ""; return; }
  try {
    const r = await fetch(`http://127.0.0.1:8787/api/assist?q=${encodeURIComponent(q)}`);
    const items = await r.json();
    out.innerHTML = items.length
      ? items.map(m => `<a class="m" href="${esc(m.url)}" target="_blank">${esc(m.title.slice(0, 80))}<div class="cat">${esc(m.category)}</div></a>`).join("")
      : `<div class="off" style="color:#5c6b7a">No matches in the register.</div>`;
  } catch {
    out.innerHTML = `<div class="off">Hermes server offline — run <b>python -m hermes serve</b></div>`;
  }
}
