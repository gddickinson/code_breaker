/* Teach-yourself guides for each puzzle, and for breaking ciphers by hand. */
let GUIDES = null;
async function guides() { if (!GUIDES) GUIDES = await (await fetch("/static/tutorials.json")).json(); return GUIDES; }

route(/^\/learn$/, async () => {
  const g = await guides();
  view().innerHTML = `<p class="kicker">// TRAINING</p><h1>Learn to solve it yourself</h1><p class="lead">Step-by-step methods you can do with your own hands and head.</p><div class="grid">${g.map(t => `<a class="card" href="#/learn/${esc(t.id)}"><b>${esc(t.title)}</b><span>${esc(t.lead)}</span></a>`).join("")}</div>`;
}, "learn");

route(/^\/learn\/(\w+)$/, async id => {
  const g = await guides(), i = g.findIndex(t => t.id === id);
  if (i < 0) { view().innerHTML = "<h1>Guide not found</h1>"; return; }
  const t = g[i], prev = g[i - 1], next = g[i + 1];
  let done = {}; try { done = JSON.parse(localStorage.getItem("guide-" + id) || "{}"); } catch { done = {}; }
  const save = () => { try { localStorage.setItem("guide-" + id, JSON.stringify(done)); } catch { /* optional progress only */ } };
  const pics = diagramsFor()[id] || [];
  const algs = s => s ? `<div class="algs">${s.split("|").map(a => `<code>${esc(a)}</code>${t.id === "cube" ? `<a href="#/puzzles/cube" data-alg="${esc(a)}">Try it</a>` : ""}`).join("")}</div>` : "";
  view().innerHTML = `<a href="#/learn">← All guides</a><h1>${esc(t.title)}</h1><p class="lead">${esc(t.lead)}</p><p>${esc(t.intro)}</p>
    <ol class="guide">${t.steps.map((s, n) => `<li class="${done[n] ? "done" : ""}"><div class="panel"><label class="stepchk"><input type="checkbox" class="check" data-n="${n}" ${done[n] ? "checked" : ""}> <h3>Step ${n + 1}: ${esc(s[0])}</h3></label>${pics[n] ? `<div class="gdfig">${pics[n]}</div>` : ""}<p>${esc(s[1])}</p>${algs(s[2])}</div></li>`).join("")}</ol>
    ${t.table ? table(t.table[0], t.table.slice(1)) : ""}
    <div class="verdict">${esc(t.tip)}</div><p><a class="cta" href="${esc(t.puzzle)}">Practise now</a></p>
    <nav class="eventnav">${prev ? `<a href="#/learn/${esc(prev.id)}">← ${esc(prev.title)}</a>` : "<span></span>"}${next ? `<a href="#/learn/${esc(next.id)}">${esc(next.title)} →</a>` : ""}</nav>`;
  document.querySelectorAll("[data-n]").forEach(c => { c.onchange = () => { done[c.dataset.n] = c.checked; save(); c.closest("li").classList.toggle("done", c.checked); }; });
  document.querySelectorAll("[data-alg]").forEach(a => { a.onclick = () => { window.PENDING_ALG = a.dataset.alg; }; });
}, "learn");

const GUIDE_FOR = { "/puzzles/cube": "cube", "/puzzles/sudoku": "sudoku", "/puzzles/lights": "lights", "/puzzles/mastermind": "mastermind", "/puzzles/sliding": "sliding", "/puzzles/hanoi": "hanoi", "/puzzles/queens": "queens", "/puzzles/knight": "knight", "/puzzles/nonogram": "nonogram" };
window.afterRender = hash => { const id = GUIDE_FOR[hash]; if (id) view().insertAdjacentHTML("beforeend", `<p><a class="cta" href="#/learn/${id}">Learn to solve this yourself</a></p>`); };
