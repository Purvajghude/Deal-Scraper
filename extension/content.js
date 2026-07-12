// Hermes Assistant — product-page overlay for Amazon.in / Flipkart.
// Talks only to the local Hermes server; nothing leaves the machine.

const HERMES = "http://127.0.0.1:8787";

function productInfo() {
  const host = location.hostname;
  let title = "", price = null;
  if (host.includes("amazon.in")) {
    title = document.querySelector("#productTitle")?.textContent.trim() || "";
    const whole = document.querySelector(".a-price .a-price-whole")?.textContent || "";
    price = parseFloat(whole.replace(/[^\d.]/g, "")) || null;
  } else if (host.includes("flipkart.com")) {
    title = document.querySelector("h1 span")?.textContent.trim()
         || document.querySelector("h1")?.textContent.trim() || "";
    const el = [...document.querySelectorAll("div")].find(d =>
      /^₹[\d,]+$/.test(d.textContent.trim()) && d.children.length === 0);
    price = el ? parseFloat(el.textContent.replace(/[^\d.]/g, "")) : null;
  }
  return { title, price };
}

async function hermes(path, opts) {
  try {
    const r = await fetch(HERMES + path, opts);
    return r.ok ? await r.json() : null;
  } catch {
    return null; // Hermes server not running — stay invisible
  }
}

function panel(html) {
  let el = document.getElementById("hermes-panel");
  if (!el) {
    el = document.createElement("div");
    el.id = "hermes-panel";
    document.body.appendChild(el);
  }
  el.innerHTML = html;
  return el;
}

async function main() {
  const { title, price } = productInfo();
  if (!title) return;

  // any matching offers already in the register? (brand = first two words)
  const q = title.split(/\s+/).slice(0, 2).join(" ");
  const matches = (await hermes(`/api/assist?q=${encodeURIComponent(q)}`)) || [];
  const status = await hermes("/api/status");
  if (status === null) return; // server offline

  const esc = s => s.replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const matchHtml = matches.length
    ? `<div class="h-sec">Possible offers in your register</div>` + matches.slice(0, 4).map(m =>
        `<a class="h-match" href="${esc(m.url)}" target="_blank">${esc(m.title.slice(0, 70))}</a>`).join("")
    : "";

  const el = panel(`
    <div class="h-head">HERMES <button class="h-close" title="Hide">✕</button></div>
    <div class="h-title">${esc(title.slice(0, 70))}</div>
    <div class="h-price">${price ? "₹" + price.toLocaleString("en-IN") : "price not detected"}</div>
    <button class="h-watch">📈 Watch this price</button>
    <div class="h-note"></div>
    ${matchHtml}
  `);

  el.querySelector(".h-close").onclick = () => el.remove();
  el.querySelector(".h-watch").onclick = async () => {
    const r = await hermes("/api/watchlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: location.href.split("?")[0], label: title.slice(0, 80) }),
    });
    el.querySelector(".h-note").textContent =
      r && r.ok ? `Watching — first reading ${r.first_price ? "₹" + r.first_price.toLocaleString("en-IN") : "pending"}.`
                : (r && r.error) || "Could not add (is Hermes running?)";
  };
}

// product pages render late on both sites
setTimeout(main, 1500);
