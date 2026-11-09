/* A live view of simulated annealing breaking a substitution cipher. */
route(/^\/machine\/anneal$/, async () => {
  const data = await api("/machines/anneal");
  const tri = Float32Array.from(data.trigrams);
  const plain = [...data.passage].map(idx);
  view().innerHTML = `${backLink}<h1>Watch a cipher break</h1>
    <p class="lead">The computer holds a random guess at the alphabet. It swaps two letters and keeps the swap if the text looks more like English. Early on it also accepts some bad swaps, which stops it getting stuck.</p>
    <div class="panel"><button id="go">Start</button><button id="new" class="alt">New passage</button><span class="mute" id="st"></span></div>
    <div class="panel"><h3>Current best reading</h3><div class="anneal" id="txt" aria-live="off"></div><div class="keygrid" id="key"></div><svg class="chart" id="plot" viewBox="0 0 900 160" role="img" aria-label="Score over time"></svg><p class="mute">Green cells are letters the search has got right. It does not know this: only you can see it, because this demo knows the real answer.</p></div>`;
  const secret = [...Array(26).keys()];
  for (let i = 25; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [secret[i], secret[j]] = [secret[j], secret[i]]; }
  const ct = plain.map(p => secret[p]), inverse = []; secret.forEach((c, p) => { inverse[c] = p; });
  let run = null, hist = [];
  const draw = a => {
    const k = a.bestKey;
    $("#txt").textContent = a.text(k);
    $("#key").innerHTML = [...AZ].map((c, i) => `<div class="${k[i] === inverse[i] ? "good" : ""}">${c}→${AZ[k[i]]}</div>`).join("");
    hist.push(a.score);
    const lo = Math.min(...hist), hi = Math.max(...hist), n = Math.max(hist.length - 1, 1);
    $("#plot").innerHTML = `<text x="10" y="18" class="charttitle">Language score</text><polyline fill="none" stroke="var(--c1)" stroke-width="2" points="${hist.map((v, i) => `${40 + i / n * 840},${145 - (v - lo) / (hi - lo || 1) * 110}`).join(" ")}"/>`;
    $("#st").textContent = `  ${a.done.toLocaleString()} of ${a.total.toLocaleString()} swaps tried. ${Math.round(k.filter((v, i) => v === inverse[i]).length / 26 * 100)}% of the alphabet correct.`;
  };
  $("#go").onclick = () => {
    if (run) return;
    const a = new SubAnneal(ct, tri, 45000, Math.floor(Math.random() * 1e9));
    hist = [];
    const frame = () => {
      if (!location.hash.startsWith("#/machine/anneal")) { run = null; return; }
      const done = a.step(160);
      draw(a);
      if (done) { run = null; return; }
      run = requestAnimationFrame(frame);
    };
    run = requestAnimationFrame(frame);
  };
  $("#new").onclick = () => render();
}, "machines");
