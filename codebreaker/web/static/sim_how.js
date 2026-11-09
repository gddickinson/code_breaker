/* How Codes Break: interactive illustrations of frequency, key length and transposition attacks. */
const ENGLISH = [8.2, 1.5, 2.8, 4.3, 12.7, 2.2, 2.0, 6.1, 7.0, 0.15, 0.77, 4.0, 2.4, 6.7, 7.5, 1.9, 0.095, 6.0, 6.3, 9.1, 2.8, 0.98, 2.4, 0.15, 2.0, 0.074];
const SAMPLE = "THE OLD LIGHTHOUSE KEEPER WROTE EVERY EVENING IN A SMALL GREEN NOTEBOOK NOBODY IN THE VILLAGE KNEW WHAT HE RECORDED THERE AND WHEN THE WINTER STORMS CAME HE WOULD CLIMB THE STAIRS ALONE AND WATCH THE SHIPS GO PAST THE ROCKS".replace(/ /g, "");
const shiftText = (t, k) => [...t].map(c => AZ[mod26(idx(c) + k)]).join("");
const counts = t => { const c = Array(26).fill(0); [...t].forEach(x => { c[idx(x)]++; }); return c; };

function compareBars(obs, exp) {
  const w = 900, h = 190, max = Math.max(...obs, ...exp), bw = (w - 60) / 26, Y = v => 160 - v / max * 135;
  const bars = AZ.split("").map((c, i) => `<g><title>${c}: ${obs[i].toFixed(1)}% in this text, ${exp[i].toFixed(1)}% in English</title><rect x="${44 + i * bw + 2}" y="${Y(obs[i])}" width="${bw - 8}" height="${160 - Y(obs[i])}" rx="3" fill="var(--c1)"/><line x1="${44 + i * bw}" x2="${44 + (i + 1) * bw - 4}" y1="${Y(exp[i])}" y2="${Y(exp[i])}" stroke="var(--c2)" stroke-width="3"/><text x="${44 + i * bw + bw / 2 - 2}" y="178" text-anchor="middle" class="axisl">${c}</text></g>`).join("");
  return `<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Letter frequencies compared with English">${bars}</svg><div class="legend"><span><i style="background:var(--c1)"></i>This text</span><span><i style="background:var(--c2);border-radius:2px"></i>English</span></div>`;
}

route(/^\/how$/, async () => {
  const items = [["frequency", "Frequency analysis", "Slide a shifted alphabet until its shape fits English."], ["keylength", "Finding the key length", "Watch a hidden period rise out of a Vigenere cipher."], ["columns", "Rebuilding a transposition", "Swap columns by hand, or let a search do it."], ["anneal", "Simulated annealing", "Random guessing turns into English.", "machine/anneal"], ["bombe", "Contradiction search", "A wrong guess destroys itself.", "machine/bombe"]];
  const sys = [["aes", "Inside AES", "Follow one block through all ten rounds."], ["ecb", "The ECB picture", "See why encrypting blocks separately leaks an image."], ["avalanche", "The avalanche effect", "Flip one bit and watch the ciphertext change."], ["feistel", "A Feistel network", "Step through Simplified DES bit by bit."], ["dh", "Key exchange on a clock", "Agree a secret in public with modular arithmetic."], ["rsa", "RSA arithmetic", "Fast exponentiation, one bit at a time."], ["colossus", "Colossus", "Count tape agreements until the wheel setting stands out."]];
  const card = ([id, n, d, href]) => `<a class="card" href="#/${href || `how/${id}`}"><b>${n}</b><span>${d}</span></a>`;
  view().innerHTML = `<p class="kicker">// HOW_IT_WORKS</p><h1>How codes break</h1><p class="lead">Interactive illustrations of the main ideas behind codebreaking, and simulations of the computer systems that do it.</p>
    <h2>Breaking classical ciphers</h2><div class="grid">${items.map(card).join("")}</div><h2>Inside computer cryptography</h2><div class="grid">${sys.map(card).join("")}</div>`;
}, "how");

const howBack = '<a href="#/how">← How codes break</a>';

route(/^\/how\/frequency$/, async () => {
  const secret = 3 + Math.floor(Math.random() * 22), ct = shiftText(SAMPLE, secret);
  view().innerHTML = `${howBack}<h1>Frequency analysis</h1><p class="lead">In English, E is common and Z is rare. A Caesar shift moves that pattern sideways. Slide it back until the bars match the lines.</p>
    <div class="panel"><label for="s">Shift to undo: <b id="v"></b></label><input id="s" type="range" min="0" max="25" value="0"><button id="best" class="alt">Find the best fit</button><div id="c"></div><h3>Reading</h3><pre id="o"></pre><p id="n" class="mute"></p></div>`;
  const fit = k => { const c = counts(shiftText(ct, -k)), n = ct.length; return c.reduce((a, x, i) => a + (x - ENGLISH[i] * n / 100) ** 2 / (ENGLISH[i] * n / 100), 0); };
  const draw = () => {
    const k = +$("#s").value, t = shiftText(ct, -k), n = t.length;
    $("#v").textContent = k; $("#c").innerHTML = compareBars(counts(t).map(x => x / n * 100), ENGLISH); $("#o").textContent = t.slice(0, 130);
    $("#n").textContent = `Mismatch with English (chi-squared): ${fit(k).toFixed(0)}. Lower is better.`;
  };
  $("#s").oninput = draw; $("#best").onclick = () => { $("#s").value = [...Array(26).keys()].reduce((b, k) => fit(k) < fit(b) ? k : b, 0); draw(); }; draw();
}, "how");

route(/^\/how\/keylength$/, async () => {
  view().innerHTML = `${howBack}<h1>Finding the key length</h1><p class="lead">Take every Nth letter. If N matches the key length, those letters share one shift, and their index of coincidence jumps towards the English value.</p>
    <div class="panel"><label for="k">Secret keyword</label><input id="k" value="LANTERN"><div id="c"></div><p id="n"></p></div>`;
  const icOf = c => { const n = c.length; if (n < 2) return 0; const f = counts(c); return f.reduce((a, x) => a + x * (x - 1), 0) / (n * (n - 1)); };
  const draw = () => {
    const key = clean($("#k").value) || "A";
    const t = [...(SAMPLE + SAMPLE + SAMPLE)].map((c, i) => AZ[(idx(c) + idx(key[i % key.length])) % 26]).join("");
    const rows = [...Array(20).keys()].map(i => { const p = i + 1; return { p, v: [...Array(p).keys()].reduce((a, s) => a + icOf([...t].filter((_, j) => j % p === s).join("")), 0) / p }; });
    const w = 900, h = 210, top = 0.09, Y = v => 175 - v / top * 150, bw = (w - 70) / 20;
    $("#c").innerHTML = `<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Index of coincidence by candidate key length"><line x1="50" x2="${w - 10}" y1="${Y(0.066)}" y2="${Y(0.066)}" stroke="var(--line)" stroke-dasharray="4 4"/><text x="${w - 12}" y="${Y(0.066) - 5}" text-anchor="end" class="axisl">English 0.066</text>${rows.map((r, i) => `<g><title>Period ${r.p}: IC ${r.v.toFixed(3)}</title><rect x="${54 + i * bw}" y="${Y(r.v)}" width="${bw - 6}" height="${175 - Y(r.v)}" rx="3" fill="${r.p % key.length === 0 ? "var(--c2)" : "var(--c1)"}"/><text x="${54 + i * bw + (bw - 6) / 2}" y="192" text-anchor="middle" class="axisl">${r.p}</text></g>`).join("")}<text x="50" y="208" class="axisl">Candidate key length</text></svg>`;
    $("#n").textContent = `The key has ${key.length} letters. Pink bars are its multiples, which is where the hidden period appears.`;
  };
  $("#k").oninput = draw; draw();
}, "how");

route(/^\/how\/columns$/, async () => {
  const COMMON = "TH HE IN ER AN RE ON AT EN ND TI ES OR TE OF ED IS IT AL AR ST TO NT NG SE HA AS OU IO LE VE CO ME DE HI RI RO IC NE EA RA CE".split(" ");
  const plain = SAMPLE.slice(0, 84), W = 7, rows = Math.floor(plain.length / W);
  let order = [...Array(W).keys()].sort(() => Math.random() - 0.5), picked = null, timer = null;
  const cols = [...Array(W).keys()].map(c => [...Array(rows).keys()].map(r => plain[r * W + c]));
  const text = o => [...Array(rows).keys()].map(r => o.map(c => cols[c][r]).join("")).join("");
  const fit = o => { const t = text(o); let s = 0; for (let i = 0; i < t.length - 1; i++) s += COMMON.includes(t.slice(i, i + 2)) ? 1 : 0; return s; };
  view().innerHTML = `${howBack}<h1>Rebuilding a transposition</h1><p class="lead">Every letter is correct, but the columns are out of order. Select two columns to swap them, or let the search use common letter pairs to find the order.</p>
    <div class="panel"><div id="g" class="scroll"></div><button id="auto">Let the search solve it</button><button id="shuf" class="alt">Shuffle</button><p id="n" class="mute"></p></div>`;
  const draw = () => {
    $("#g").innerHTML = `<div class="colgrid">${order.map((c, i) => `<button type="button" class="col ${picked === i ? "picked" : ""}" data-i="${i}" aria-label="Column ${i + 1}">${cols[c].map(x => `<span>${x}</span>`).join("")}</button>`).join("")}</div>`;
    document.querySelectorAll(".col").forEach(b => { b.onclick = () => { const i = +b.dataset.i; if (picked === null) picked = i; else { [order[picked], order[i]] = [order[i], order[picked]]; picked = null; } draw(); }; });
    const ok = text(order) === plain.slice(0, rows * W);
    $("#n").textContent = `${fit(order)} common letter pairs.${ok ? " Solved: the text reads across." : ""}`;
  };
  $("#shuf").onclick = () => { clearInterval(timer); order = order.sort(() => Math.random() - 0.5); picked = null; draw(); };
  $("#auto").onclick = () => {
    clearInterval(timer);
    timer = setInterval(() => {
      if (!location.hash.endsWith("/how/columns")) return clearInterval(timer);
      let best = null, bs = fit(order);
      for (let a = 0; a < W; a++) for (let b = a + 1; b < W; b++) { const o = [...order]; [o[a], o[b]] = [o[b], o[a]]; const s = fit(o); if (s > bs) { bs = s; best = o; } }
      if (best) { order = best; draw(); } else clearInterval(timer);
    }, 420);
  };
  draw();
}, "how");
