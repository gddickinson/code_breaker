/* Theory simulations, part two: inference, quantum factoring and block-cipher attacks. */
THSIMS.belief = el => {
  const truth = [1, 0, 1, 1, 0, 1, 0]; let rx = [...truth];
  el.innerHTML = `<p class="mute">Valid codeword shown. Select bits to flip them, as if damaged in transit.</p><div id="b" class="bitrow"></div><label for="c">Channel confidence: <b id="v"></b></label><input id="c" type="range" min="0.5" max="4" step="0.1" value="1.6"><div id="g" class="scroll"></div><div id="o"></div>`;
  const draw = () => {
    const c = +$("#c").value; $("#v").textContent = c.toFixed(1);
    $("#b").innerHTML = rx.map((v, i) => `<button type="button" data-i="${i}" class="${v !== truth[i] ? "bad" : ""}">${v}</button>`).join("");
    document.querySelectorAll("#b button").forEach(b => { b.onclick = () => { rx[+b.dataset.i] ^= 1; draw(); }; });
    const llr = rx.map(v => (v ? -c : c)), d = bpDecode(llr), W = 640, xN = i => 40 + i * 90, xC = i => 140 + i * 180;
    const edges = HAMMING.flatMap((r, ci) => r.flatMap((v, n) => (v ? [`<line x1="${xC(ci)}" y1="40" x2="${xN(n)}" y2="150" stroke="var(--c1)" opacity=".5"/>`] : []))).join("");
    const checks = HAMMING.map((_, ci) => `<rect x="${xC(ci) - 13}" y="26" width="26" height="26" fill="var(--c4)"/>`).join("");
    const vars = d.posterior.map((p, n) => `<circle cx="${xN(n)}" cy="150" r="17" fill="${p < 0 ? "var(--c2)" : "var(--c1)"}"/><text x="${xN(n)}" y="155" text-anchor="middle" class="clockv">${p < 0 ? 1 : 0}</text><text x="${xN(n)}" y="186" text-anchor="middle" class="axisl">${p.toFixed(1)}</text>`).join("");
    $("#g").innerHTML = `<svg class="chart" viewBox="0 0 ${W} 200" role="img" aria-label="Tanner graph with final beliefs"><text x="10" y="16" class="axisl">Parity checks</text>${edges}${checks}${vars}</svg>`;
    const fixed = JSON.stringify(d.bits) === JSON.stringify(truth);
    $("#o").innerHTML = `<p class="reading">Decoded: ${d.bits.join("")} ${fixed ? "(original recovered)" : "(not the original codeword)"}</p><p class="mute">Numbers are final log-odds: positive favours 0, negative favours 1. ${parityOK(d.bits) ? "All parity checks pass." : "A parity check still fails."}</p>`;
  };
  $("#c").oninput = draw; draw();
};

THSIMS.hmm = async el => {
  el.innerHTML = '<p class="mute">Loading letter statistics…</p>';
  const m = await api("/theory/bigrams"), base = m.sample.slice(0, 220), tv = [...base].map(c => idx(c));
  el.innerHTML = `<label for="n">Noise: <b id="v"></b></label><input id="n" type="range" min="0.02" max="0.5" step="0.02" value="0.2"><div id="o"></div>`;
  const draw = () => {
    const noise = +$("#n").value, r = rng(77), obs = tv.map(v => (r() < noise ? Math.floor(r() * 26) : v)), em = (s, o) => (s === o ? 1 - noise + noise / 26 : noise / 26);
    const fb = hmmDecode(obs, m.transition, em), vt = viterbi(obs, m.transition, em), acc = a => a.filter((v, i) => v === tv[i]).length / tv.length * 100, show = a => a.map((v, i) => (v === tv[i] ? AZ[v] : `<mark>${AZ[v]}</mark>`)).join("");
    $("#v").textContent = `${Math.round(noise * 100)}%`;
    $("#o").innerHTML = `<div class="tiles"><div class="tile"><b>${acc(obs).toFixed(0)}%</b><span>Correct in the noisy text</span></div><div class="tile"><b>${acc(fb).toFixed(0)}%</b><span>After forward-backward</span></div><div class="tile"><b>${acc(vt).toFixed(0)}%</b><span>After Viterbi</span></div></div><h3>Noisy</h3><pre>${show(obs)}</pre><h3>Forward-backward</h3><pre>${show(fb)}</pre><p class="mute">Highlighted letters are wrong. The model only knows letter-pair statistics.</p>`;
  };
  $("#n").oninput = draw; draw();
};

THSIMS.variational = el => {
  const n = 64;
  el.innerHTML = `<label for="f">Pixels flipped: <b id="v"></b></label><input id="f" type="range" min="0.02" max="0.35" step="0.01" value="0.18"><div class="three">${[["a", "Noisy"], ["b", "Mean-field"], ["c", "Gibbs sampling"]].map(([i, l]) => `<figure><canvas id="${i}" width="${n}" height="${n}" class="bits" role="img" aria-label="${l}"></canvas><figcaption id="l${i}">${l}</figcaption></figure>`).join("")}</div>`;
  const put = (id, v) => { const g = $("#" + id).getContext("2d"), im = g.createImageData(n, n); v.forEach((x, i) => { const c = Math.round((x + 1) * 127.5); im.data[i * 4] = c * 0.2; im.data[i * 4 + 1] = c; im.data[i * 4 + 2] = c; im.data[i * 4 + 3] = 255; }); g.putImageData(im, 0, 0); };
  const draw = () => { const f = +$("#f").value, d = isingData(n, f, 3), h = 0.5 * Math.log((1 - f) / f), t0 = performance.now(), mf = meanField(d.noisy, n, 0.6, h, 15).q, t1 = performance.now(), gi = gibbs(d.noisy, n, 0.6, h, 60, 5), t2 = performance.now(); $("#v").textContent = `${Math.round(f * 100)}%`; put("a", d.noisy); put("b", mf); put("c", gi); $("#la").textContent = `Noisy: ${(agreement(d.noisy, d.clean) * 100).toFixed(1)}%`; $("#lb").textContent = `Mean-field: ${(agreement(mf, d.clean) * 100).toFixed(1)}%, ${(t1 - t0).toFixed(1)} ms`; $("#lc").textContent = `Gibbs sampling: ${(agreement(gi, d.clean) * 100).toFixed(1)}%, ${(t2 - t1).toFixed(1)} ms`; };
  $("#f").oninput = draw; draw();
};

THSIMS.shor = el => {
  const CASES = [[15, 7, 8], [15, 2, 8], [15, 11, 8], [21, 2, 9], [21, 5, 9], [35, 2, 10]];
  el.innerHTML = `<label for="c">Number and base</label><select id="c">${CASES.map(([N, a, q], i) => `<option value="${i}">Factor ${N} using a = ${a}, with ${q} qubits</option>`).join("")}</select><div id="o"></div>`;
  const draw = () => {
    const [N, a, q] = CASES[+$("#c").value], Q = 2 ** q, p = shorProbs(N, a, q), mx = Math.max(...p), bw = 860 / Q, vals = []; let x = 1;
    for (let i = 0; i < 16; i++) { vals.push(x); x = x * a % N; }
    let r = 1; while (modPow(a, r, N) !== 1) r++;
    const res = shorFactor(N, a, q, 11);
    $("#o").innerHTML = `<h3>Powers of ${a} mod ${N}</h3><pre>${vals.join(", ")} …\nThe period is r = ${r}.</pre><h3>Probability of each measurement after the Fourier transform</h3><svg class="chart" viewBox="0 0 900 190" role="img" aria-label="Measurement probabilities with peaks at multiples of Q over r">${p.map((v, i) => (v > mx * 0.01 ? `<rect x="${20 + i * bw}" y="${170 - v / mx * 150}" width="${Math.max(bw, 2)}" height="${v / mx * 150}" fill="var(--c2)"><title>k = ${i}: ${(v * 100).toFixed(2)}%</title></rect>` : "")).join("")}<line x1="20" x2="880" y1="170" y2="170" stroke="var(--line)"/></svg><p class="mute">Peaks fall near multiples of Q/r = ${(Q / r).toFixed(1)}.</p>${res.factors ? table(["Measured k", "Period found", "Trials", "Factors"], [[res.k ?? "n/a", res.r ?? "n/a", res.tries, res.factors.join(" × ")]]) : '<p class="err">This base gives no factor. Choose another.</p>'}<p class="mute">The ${Q}-entry state vector is simulated classically, which is why only tiny numbers are practical here.</p>`;
  };
  $("#c").onchange = draw; draw();
};

THSIMS.differential = el => {
  const t = ddt();
  el.innerHTML = `<h3>Difference table of the PRESENT S-box</h3><div class="scroll"><table class="heat"><thead><tr><th scope="col">Δin / Δout</th>${[...Array(16).keys()].map(i => `<th scope="col">${i.toString(16)}</th>`).join("")}</tr></thead><tbody>${t.map((r, i) => `<tr><th scope="row">${i.toString(16)}</th>${r.map(v => `<td class="ddt" style="background:rgba(224,80,140,${i === 0 ? 0.05 : v / 6})">${v || ""}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
    <h3>Attack a two-round toy cipher</h3><div class="row"><div><label for="k">Last round key (0 to 15): <b id="v"></b></label><input id="k" type="range" min="0" max="15" value="9"></div></div><div id="o"></div>`;
  const draw = () => { const k2 = +$("#k").value; $("#v").textContent = k2; const c = diffAttack([6, 11, k2]), best = Math.max(...c); $("#o").innerHTML = barChart({ title: "Pairs consistent with each last-round key guess", items: c.map((v, g) => ({ label: `key ${g}`, value: v, hit: g === k2 })), unit: "pairs" }) + `<p class="mute">The pink bar is the true key. ${c[k2] === best ? "It is the top candidate." : "It is close to the top, and a little more data would separate it."}</p>`; };
  $("#k").oninput = draw; draw();
};

THSIMS.rho = el => {
  el.innerHTML = `<label for="n">Number to factor</label><input id="n" type="number" value="8051"><div id="o"></div>`;
  const draw = () => {
    const n = Math.floor(+$("#n").value);
    if (!(n > 3 && n < 94906265)) { $("#o").innerHTML = '<p class="mute">Choose a number from 4 to 94,906,264.</p>'; return; }
    let r = null; for (let c = 1; c < 12 && !(r && r.factor); c++) r = pollardRho(n, c);
    if (!r.factor) { $("#o").innerHTML = '<p class="reading">No factor found. The number may be prime.</p>'; return; }
    const p = r.factor, m = r.path.map(v => v % p);
    let trial = 2; while (n % trial) trial++;
    $("#o").innerHTML = `<div class="tiles"><div class="tile"><b>${p} × ${n / p}</b><span>Factors found</span></div><div class="tile"><b>${r.steps}</b><span>Rho steps</span></div><div class="tile"><b>${trial - 1}</b><span>Trial divisions needed</span></div></div><h3>The walk modulo the hidden factor ${p}</h3><pre>${m.slice(0, 48).join(" → ")}</pre><p class="mute">Once a value repeats modulo ${p}, the walk is trapped in a cycle, and the tortoise and hare collide.</p>`;
  };
  $("#n").oninput = draw; draw();
};
