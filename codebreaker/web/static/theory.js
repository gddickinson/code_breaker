/* Theory section: explanations and interactive simulations of the underlying algorithms. */
let THEORY = null;
async function theory() { if (!THEORY) THEORY = await (await fetch("/static/theory.json")).json(); return THEORY; }
const THSIMS = {};
const fmt = (v, d = 3) => Number(v).toFixed(d);

route(/^\/theory$/, async () => {
  const t = await theory(), g = [...new Set(t.map(x => x.group))];
  view().innerHTML = `<p class="kicker">// THEORY</p><h1>Theory of codes and codebreaking</h1><p class="lead">Information theory, inference and the algorithms of cryptanalysis, each with examples, a working simulation, and how it is used to solve real problems.</p>
    ${g.map(n => `<section class="family"><h2>${esc(n)}</h2><div class="grid">${t.filter(x => x.group === n).map(x => `<a class="card" href="#/theory/${esc(x.id)}"><b>${esc(x.title)}</b><span>${esc(x.lead)}</span></a>`).join("")}</div></section>`).join("")}<p><a href="#/math">See also: the maths of codebreaking →</a></p>`;
}, "theory");

route(/^\/theory\/(\w+)$/, async id => {
  const t = await theory(), i = t.findIndex(x => x.id === id);
  if (i < 0) { view().innerHTML = "<h1>Topic not found</h1>"; return; }
  const x = t[i], prev = t[i - 1], next = t[i + 1], rows = x.table;
  view().innerHTML = `<a href="#/theory">← Theory</a><p class="kicker">// ${esc(x.group)}</p><h1>${esc(x.title)}</h1><p class="lead">${esc(x.lead)}</p>
    ${x.sections.map(([h, b]) => `<h2>${esc(h)}</h2><p>${esc(b)}</p>`).join("")}
    ${rows ? `<h2>The catalogue</h2><div class="scroll"><table><thead><tr>${rows[0].map(c => `<th scope="col">${esc(c)}</th>`).join("")}</tr></thead><tbody>${rows.slice(1).map(r => `<tr><td>${esc(r[0])}</td><td>${esc(r[1])}</td><td>${esc(r[2])}</td><td><a href="${esc(r[3])}">Open</a></td></tr>`).join("")}</tbody></table></div>` : ""}
    <div class="panel"><h3>Worked example: ${esc(x.example[0])}</h3><p class="reading">${esc(x.example[1])}</p></div>
    ${x.sim ? `<h2>Simulation</h2><div class="panel" id="sim"></div>` : ""}
    <h2>Use in solving problems</h2><p>${esc(x.solve)}</p>${x.links ? `<div class="row">${x.links.map(([l, h]) => `<a class="cta" href="${esc(h)}">${esc(l)}</a>`).join("")}</div>` : ""}
    <nav class="eventnav">${prev ? `<a href="#/theory/${esc(prev.id)}">← ${esc(prev.title)}</a>` : "<span></span>"}${next ? `<a href="#/theory/${esc(next.id)}">${esc(next.title)} →</a>` : ""}</nav>`;
  if (x.sim && THSIMS[x.sim]) await THSIMS[x.sim]($("#sim"));
}, "theory");

THSIMS.entropy = el => {
  el.innerHTML = `<label for="t">Text to analyse</label><textarea id="t">In the beginning was the word and the word was with the code</textarea><div id="o"></div>`;
  const draw = () => {
    const s = $("#t").value.toUpperCase().replace(/[^A-Z]/g, "");
    if (s.length < 2) { $("#o").innerHTML = '<p class="mute">Type at least two letters.</p>'; return; }
    const c = countsOf(s), n = s.length, items = Object.entries(c).sort((a, b) => b[1] - a[1]).slice(0, 12).map(([k, v]) => ({ label: k, value: +(-(v / n) * Math.log2(v / n)).toFixed(3), hit: false }));
    $("#o").innerHTML = `<div class="tiles"><div class="tile"><b>${fmt(entropyOf(s))}</b><span>H: bits per letter</span></div><div class="tile"><b>${fmt(condEntropy(s))}</b><span>H given previous letter</span></div><div class="tile"><b>4.700</b><span>Maximum for 26 letters</span></div></div>${barChart({ title: "Bits each letter contributes", items, unit: "bits" })}`;
  };
  $("#t").oninput = draw; draw();
};

function treeSVG(root) {
  let leaf = 0; const pos = new Map(); const depth = (n, d = 0) => { if (!n.l) { pos.set(n, [leaf++, d]); return leaf - 1; } const a = depth(n.l, d + 1), b = depth(n.r, d + 1); const x = (a + b) / 2; pos.set(n, [x, d]); return x; }; depth(root);
  const W = Math.max(leaf * 44, 200), H = Math.max(...[...pos.values()].map(p => p[1])) * 58 + 60, P = n => [pos.get(n)[0] * 44 + 26, pos.get(n)[1] * 58 + 24];
  let e = "", v = ""; const walk = n => { const [x, y] = P(n); if (n.l) { for (const [c, b] of [[n.l, "0"], [n.r, "1"]]) { const [a, d] = P(c); e += `<line x1="${x}" y1="${y}" x2="${a}" y2="${d}" stroke="var(--c1)"/><text x="${(x + a) / 2 - 6}" y="${(y + d) / 2}" class="axisl">${b}</text>`; walk(c); } v += `<circle cx="${x}" cy="${y}" r="10" fill="var(--c4)"/>`; } else v += `<circle cx="${x}" cy="${y}" r="14" fill="var(--c2)"/><text x="${x}" y="${y + 4}" text-anchor="middle" class="clockv">${esc(n.s === " " ? "␣" : n.s)}</text>`; }; walk(root);
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" style="max-width:${W}px" role="img" aria-label="Huffman code tree">${e}${v}</svg>`;
}
THSIMS.huffman = el => {
  el.innerHTML = `<label for="t">Text to compress</label><textarea id="t">THIS IS AN EXAMPLE OF HUFFMAN CODING</textarea><div id="o"></div>`;
  const draw = () => {
    const s = $("#t").value.toUpperCase(); if (new Set(s).size < 2 || s.length > 400) { $("#o").innerHTML = '<p class="mute">Use up to 400 characters, with at least two different ones.</p>'; return; }
    const f = countsOf(s), h = huffman(f), sf = shannonFano(f), H = entropyOf(s), a = avgLength(f, h.codes), b = avgLength(f, sf), fixed = Math.ceil(Math.log2(Object.keys(f).length));
    $("#o").innerHTML = `<div class="tiles"><div class="tile"><b>${fmt(H)}</b><span>Entropy limit</span></div><div class="tile"><b>${fmt(a)}</b><span>Huffman bits/symbol</span></div><div class="tile"><b>${fmt(b)}</b><span>Shannon-Fano</span></div><div class="tile"><b>${fixed}</b><span>Fixed-length code</span></div></div><div class="scroll">${treeSVG(h.root)}</div>${table(["Symbol", "Count", "Huffman", "Shannon-Fano"], Object.entries(f).sort((x, y) => y[1] - x[1]).map(([k, v]) => [k === " " ? "space" : k, v, h.codes[k], sf[k]]))}<h3>Message encoded</h3><pre>${esc(encode(s, h.codes).slice(0, 400))}</pre>`;
  };
  $("#t").oninput = draw; draw();
};

THSIMS.randomness = el => {
  el.innerHTML = `<label for="k">Generator</label><select id="k"><option value="good">Good pseudo-random</option><option value="biased">Biased coin (56% ones)</option><option value="lcg">Small linear congruential</option><option value="alt">Alternating pattern</option></select><div class="center"><canvas id="c" width="200" height="200" class="bits" role="img" aria-label="Output bits as a grid"></canvas></div><div id="o"></div>`;
  const draw = () => { const k = $("#k").value, b = makeBits(k, 40000, 12345), g = $("#c").getContext("2d"), im = g.createImageData(200, 200); b.forEach((v, i) => { const j = i * 4, c = v ? 0 : 230; im.data[j] = c ? 240 : 0; im.data[j + 1] = c ? 240 : 160; im.data[j + 2] = c ? 250 : 181; im.data[j + 3] = 255; }); g.putImageData(im, 0, 0); const t = randomnessTests(b); const r = (n, v, lim, ok) => [n, fmt(v), lim, ok ? "Pass" : "Fail"]; $("#o").innerHTML = table(["Test", "Statistic", "Limit at 1%", "Result"], [r("Monobit", t.monobit, "2.58", t.pass.monobit), r("Runs", t.runZ, "2.58", t.pass.runs), r("Pairs chi-squared", t.pairChi, "11.34", t.pass.pairs)]) + `<p class="mute">Passing shows only that these tests found no pattern. The first generator is not proof of true randomness.</p>`; };
  $("#k").onchange = draw; draw();
};

THSIMS.lfsr = el => {
  el.innerHTML = `<div class="row"><div><label for="s">9-bit seed</label><input id="s" value="100101101" maxlength="9"></div><div><label for="n">Bits observed: <b id="v"></b></label><input id="n" type="range" min="6" max="60" value="30"></div></div><pre id="b"></pre><div id="o"></div>`;
  const draw = () => { const seed = $("#s").value.replace(/[^01]/g, "").padEnd(9, "1").slice(0, 9).split("").map(Number), n = +$("#n").value, st = lfsr([0, 4], seed, n + 120), seen = st.slice(0, n), b = berlekampMassey(seen), pred = bmPredict(seen, b.C, b.L, 120), right = pred.filter((v, i) => v === st[n + i]).length; $("#v").textContent = n; $("#b").textContent = `Observed: ${seen.join("")}\nPredicted next: ${pred.slice(0, 40).join("")}\nTrue next:      ${st.slice(n, n + 40).join("")}`; $("#o").innerHTML = `<div class="tiles"><div class="tile"><b>${b.L}</b><span>Register length found</span></div><div class="tile"><b>${right}/120</b><span>Future bits predicted</span></div></div>`; };
  $("#s").oninput = draw; $("#n").oninput = draw; draw();
};

THSIMS.montecarlo = el => {
  el.innerHTML = `<label for="n">Darts: <b id="v"></b></label><input id="n" type="range" min="2" max="6" step="0.25" value="3"><div class="center"><svg id="p" class="disk" viewBox="0 0 300 300" role="img" aria-label="Darts in a square with a quarter circle"></svg></div><div id="o"></div>`;
  const draw = () => { const n = Math.round(10 ** +$("#n").value), r = monteCarloPi(n, 42); $("#v").textContent = n.toLocaleString(); $("#p").innerHTML = `<rect width="300" height="300" fill="none" stroke="var(--line)"/><path d="M0 300 A300 300 0 0 1 300 0 L0 0 Z" fill="none" stroke="var(--c1)"/>${r.pts.map(([x, y, a]) => `<circle cx="${y * 300}" cy="${x * 300}" r="1.6" fill="${a ? "var(--c1)" : "var(--c2)"}"/>`).join("")}`; $("#o").innerHTML = `<div class="tiles"><div class="tile"><b>${fmt(r.estimate, 4)}</b><span>Estimate of π</span></div><div class="tile"><b>${fmt(Math.abs(r.estimate - Math.PI), 4)}</b><span>Error</span></div></div><p class="mute">Up to 900 darts are drawn; all are counted.</p>`; };
  $("#n").oninput = draw; draw();
};

THSIMS.mcmc = el => {
  el.innerHTML = `<label for="s">Proposal step size: <b id="v"></b></label><input id="s" type="range" min="0.05" max="20" step="0.05" value="2.5"><div id="o"></div>`;
  const target = x => Math.exp(-((x + 2) ** 2) / 1.2) + 0.65 * Math.exp(-((x - 2.2) ** 2) / 0.9);
  const draw = () => { const st = +$("#s").value, m = metropolis(target, 6000, st, 7, 0), s = m.samples; $("#v").textContent = st.toFixed(2); const W = 860, H = 110, xs = v => 30 + (v + 6) / 12 * W, tr = s.filter((_, i) => i % 6 === 0).map((v, i) => `${i / 1000 * W + 20},${H / 2 - v * 7}`).join(" "); const bins = Array(50).fill(0); s.forEach(v => { const b = Math.floor((v + 6) / 12 * 50); if (b >= 0 && b < 50) bins[b]++; }); const mx = Math.max(...bins), bw = W / 50; $("#o").innerHTML = `<div class="tiles"><div class="tile"><b>${(m.acceptance * 100).toFixed(0)}%</b><span>Moves accepted</span></div></div><svg class="chart" viewBox="0 0 900 ${H}" role="img" aria-label="Sample trace"><text x="10" y="14" class="charttitle">Trace</text><polyline fill="none" stroke="var(--c1)" points="${tr}"/></svg><svg class="chart" viewBox="0 0 900 180" role="img" aria-label="Histogram of samples"><text x="10" y="14" class="charttitle">Where the chain spent its time</text>${bins.map((v, i) => `<rect x="${30 + i * bw}" y="${170 - v / mx * 140}" width="${bw - 2}" height="${v / mx * 140}" rx="2" fill="var(--c1)"/>`).join("")}</svg>`; };
  $("#s").oninput = draw; draw();
};
