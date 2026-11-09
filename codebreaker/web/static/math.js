/* The mathematics of codebreaking: explanations, worked examples and small calculators. */
let MATH = null;
async function maths() { if (!MATH) MATH = await (await fetch("/static/math.json")).json(); return MATH; }

const WIDGETS = {
  inverse: { html: `<div class="row"><div><label for="w1">Number</label><input id="w1" type="number" value="5"></div><div><label for="w2">Modulus</label><input id="w2" type="number" value="26"></div></div><p id="wo" class="reading"></p>`, run: () => { const a = +$("#w1").value, m = +$("#w2").value; let f = null; if (m > 1 && m < 1e6) for (let i = 1; i < m; i++) if ((((a % m) + m) % m) * i % m === 1) { f = i; break; } $("#wo").textContent = f === null ? `${a} has no inverse mod ${m}.` : `Inverse of ${a} mod ${m} is ${f}, because ${a} × ${f} ≡ 1.`; } },
  gcd: { html: `<div class="row"><div><label for="w1">a</label><input id="w1" type="number" value="1071"></div><div><label for="w2">b</label><input id="w2" type="number" value="462"></div></div><pre id="wo"></pre>`, run: () => { let a = Math.abs(+$("#w1").value), b = Math.abs(+$("#w2").value); const out = []; while (b && out.length < 60) { const q = Math.floor(a / b); out.push(`${a} = ${q} × ${b} + ${a - q * b}`); [a, b] = [b, a - q * b]; } $("#wo").textContent = `${out.join("\n")}\ngcd = ${a}`; } },
  birthday: { html: `<label for="w1">People: <b id="wv"></b></label><input id="w1" type="range" min="2" max="80" value="23"><p id="wo" class="reading"></p>`, run: () => { const n = +$("#w1").value; let p = 1; for (let i = 0; i < n; i++) p *= (365 - i) / 365; $("#wv").textContent = n; $("#wo").textContent = `Chance of a shared birthday: ${((1 - p) * 100).toFixed(1)}%.`; } },
};

route(/^\/math$/, async () => {
  const t = await maths(), tags = [...new Set(t.map(x => x.tag))];
  view().innerHTML = `<p class="kicker">// MATHEMATICS</p><h1>The maths of codebreaking</h1><p class="lead">The ideas that make ciphers work and fail, each with a worked example.</p>
    ${tags.map(g => `<section class="family"><h2>${esc(g)}</h2><div class="grid">${t.filter(x => x.tag === g).map(x => `<a class="card" href="#/math/${esc(x.id)}"><b>${esc(x.title)}</b><span>${esc(x.lead)}</span></a>`).join("")}</div></section>`).join("")}`;
}, "math");

route(/^\/math\/(\w+)$/, async id => {
  const t = await maths(), i = t.findIndex(x => x.id === id);
  if (i < 0) { view().innerHTML = "<h1>Topic not found</h1>"; return; }
  const x = t[i], prev = t[i - 1], next = t[i + 1], w = WIDGETS[x.widget];
  view().innerHTML = `<a href="#/math">← The maths of codebreaking</a><p class="kicker">// ${esc(x.tag)}</p><h1>${esc(x.title)}</h1><p class="lead">${esc(x.lead)}</p>
    ${x.sections.map(([h, b]) => `<h2>${esc(h)}</h2><p>${esc(b)}</p>`).join("")}
    <div class="panel"><h3>Worked example: ${esc(x.example[0])}</h3><p class="reading">${esc(x.example[1])}</p></div>
    ${w ? `<div class="panel"><h3>Try it</h3>${w.html}</div>` : ""}
    <h2>See it in action</h2><div class="row">${x.links.map(([l, h]) => `<a class="cta" href="${esc(h)}">${esc(l)}</a>`).join("")}</div>
    <nav class="eventnav">${prev ? `<a href="#/math/${esc(prev.id)}">← ${esc(prev.title)}</a>` : "<span></span>"}${next ? `<a href="#/math/${esc(next.id)}">${esc(next.title)} →</a>` : ""}</nav>`;
  if (w) { document.querySelectorAll("#w1,#w2").forEach(e => { e.oninput = w.run; }); w.run(); }
}, "math");

route(/^\/community$/, async () => {
  const links = await (await fetch("/static/community.json")).json(), cats = [...new Set(links.map(l => l.category))];
  view().innerHTML = `<p class="kicker">// NETWORK</p><h1>Community</h1><p class="lead">Contests, forums and resources for codebreakers and puzzlers. Links were checked when this list was built.</p>
    <div class="verdict">Read each contest's rules before entering. Some are limited to students, and many restrict AI or automated tools. Respect that, even when this app could help.</div>
    ${cats.map(c => `<section class="family"><h2>${esc(c)}</h2><div class="grid">${links.filter(l => l.category === c).map(l => `<a class="card" href="${esc(l.url)}" rel="noreferrer" target="_blank"><b>${esc(l.name)}</b><span>${esc(l.note)}</span></a>`).join("")}</div></section>`).join("")}`;
}, "community");

route(/^\/publications$/, async () => {
  let topic = "", page = 0, q = "";
  view().innerHTML = `<p class="kicker">// LIBRARY_INDEX</p><h1>Publications</h1><p class="lead">Academic papers and books on cryptology, codes and puzzles. Each record comes from Crossref and links to its DOI.</p>
    <div class="row filters"><div><label for="q">Search title, author or journal</label><input id="q" placeholder="For example, Voynich"></div><div><label for="t">Topic</label><select id="t"><option value="">All topics</option></select></div></div><p id="n" class="mute"></p><div id="r"></div><div id="p"></div>`;
  const load = async () => {
    const d = await api(`/publications?q=${encodeURIComponent(q)}&topic=${encodeURIComponent(topic)}&page=${page}`);
    if ($("#t").options.length === 1) d.topics.forEach(x => $("#t").add(new Option(`${x.topic} (${x.n})`, x.topic)));
    $("#n").textContent = `${d.total.toLocaleString()} works, most cited first`;
    $("#r").innerHTML = d.rows.map(r => `<div class="pub"><a href="${esc(r.url)}" target="_blank" rel="noreferrer">${esc(r.title)}</a><small>${esc(r.authors || "Author not listed")}${r.year ? `, ${r.year}` : ""}${r.venue ? `. ${esc(r.venue)}` : ""}</small><small class="mute">${esc(r.topic)} · cited ${r.citations} times</small></div>`).join("");
    $("#p").innerHTML = `${page > 0 ? '<button id="pv" class="alt">Previous</button>' : ""}${(page + 1) * 40 < d.total ? '<button id="nx">Next</button>' : ""}`;
    if ($("#pv")) $("#pv").onclick = () => { page--; load(); window.scrollTo(0, 0); };
    if ($("#nx")) $("#nx").onclick = () => { page++; load(); window.scrollTo(0, 0); };
  };
  let t0; $("#q").oninput = e => { clearTimeout(t0); t0 = setTimeout(() => { q = e.target.value; page = 0; load(); }, 250); };
  $("#t").onchange = e => { topic = e.target.value; page = 0; load(); };
  load();
}, "publications");
