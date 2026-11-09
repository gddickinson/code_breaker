/* Shared helpers and the hash router. All server text goes through esc(). */
const $ = (s, r = document) => r.querySelector(s);
const view = () => $("#view");
const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const state = { languages: {} };

async function api(path, body) {
  const res = await fetch("/api" + path, body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

function langSelect(id, value = "en") {
  return `<select id="${id}">${Object.entries(state.languages).map(([c, n]) => `<option value="${c}" ${c === value ? "selected" : ""}>${esc(n)}</option>`).join("")}</select>`;
}

function table(cols, rows) {
  return `<div class="scroll"><table><thead><tr>${cols.map(c => `<th scope="col">${esc(c)}</th>`).join("")}</tr></thead><tbody>${rows.map(r => `<tr>${r.map(v => `<td>${esc(v)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

/* Disable the button during slow work and show errors next to it. */
async function busy(btn, target, fn) {
  btn.disabled = true;
  const label = btn.textContent;
  btn.textContent = "Working…";
  try { await fn(); }
  catch (e) { target.innerHTML = `<p class="err">${esc(e.message)}</p>`; }
  finally { btn.disabled = false; btn.textContent = label; }
}

const routes = [];
const route = (re, fn, nav) => routes.push({ re, fn, nav });

async function render() {
  const hash = location.hash.slice(1) || "/";
  for (const r of routes) {
    const m = hash.match(r.re);
    if (!m) continue;
    document.querySelectorAll("[data-nav]").forEach(a => a.classList.toggle("on", a.dataset.nav === r.nav));
    document.querySelectorAll("nav.groups details").forEach(d => { d.classList.toggle("on", !!d.querySelector(`[data-nav="${r.nav}"]`)); d.open = false; });
    view().innerHTML = '<p class="mute">Loading…</p>';
    try { await r.fn(...m.slice(1)); }
    catch (e) { view().innerHTML = `<p class="err">${esc(e.message)}</p>`; }
    window.scrollTo(0, 0);
    view().focus({ preventScroll: true });
    return;
  }
  view().innerHTML = "<h1>Page not found</h1>";
}

document.addEventListener("click", e => { document.querySelectorAll("nav.groups details[open]").forEach(d => { if (!d.contains(e.target)) d.open = false; }); });

async function start() {
  window.addEventListener("hashchange", render);
  const data = await api("/ciphers");
  state.languages = data.languages;
  state.ciphers = data.ciphers;
  render();
}
