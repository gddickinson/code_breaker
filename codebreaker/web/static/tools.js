/* Workbench (analysis), Challenge and Translate pages. */
function freqBars(obs, exp) {
  const keys = Object.keys(obs);
  const max = Math.max(...keys.map(k => Math.max(obs[k], exp[k])), 1);
  return `<div class="bars" role="img" aria-label="Letter counts compared with expected English">${keys.map(k => `<div class="bar" title="${k}: ${obs[k]} seen, ${exp[k]} expected in English"><i style="height:${obs[k] / max * 100}%"></i><u style="bottom:${exp[k] / max * 100}%"></u></div>`).join("")}</div>
    <div class="axis">${keys.map(k => `<span>${k}</span>`).join("")}</div><p class="mute">Bars show your text. Lines show the English expectation.</p>`;
}

route(/^\/workbench$/, async () => {
  view().innerHTML = `<h1>Workbench</h1><p class="lead">Paste any ciphertext for a statistical profile and a best guess at the system.</p>
    <div class="panel"><label for="t">Ciphertext</label><textarea id="t"></textarea><button id="go">Analyse</button><button id="ab" class="alt">Autobreak</button></div><div id="abo"></div><div id="o"></div>`;
  $("#ab").onclick = ev => busy(ev.target, $("#abo"), async () => {
    const r = await api("/autobreak", { text: $("#t").value });
    $("#abo").innerHTML = `<div class="panel"><h3>Autobreak</h3><p class="mute">${esc(r.note)}</p>${r.guesses.length ? `<h3>The network's guesses</h3>${table(["System", "Probability"], r.guesses.map(g => [g.name, `${Math.round(g.probability * 100)}%`]))}` : ""}
      ${r.best ? `<h3>Best reading: ${esc(r.best.cipher)}</h3><pre>${esc(r.best.spaced)}</pre>${table(["System tried", "Word coverage", "Score"], r.results.map(x => [x.cipher, `${Math.round(x.coverage * 100)}%`, x.score.toFixed(2)]))}` : ""}</div>`;
  });
  $("#go").onclick = ev => busy(ev.target, $("#o"), async () => {
    const r = await api("/analyze", { text: $("#t").value });
    const periods = [...r.periods].sort((a, b) => b.ic - a.ic).slice(0, 6);
    $("#o").innerHTML = `<div class="panel"><h3>Likely systems</h3>${table(["Candidate", "Evidence"], r.identify.map(x => [x.family, x.evidence]))}</div>
      <div class="panel"><h3>Measurements</h3>${table(["Letters", "Index of coincidence", "Entropy (bits)"], [[r.length, r.ic, r.entropy]])}<p class="mute">English has an IC near 0.066, and uniform random letters near 0.038.</p>
      <h3>Letter frequencies</h3>${freqBars(r.frequencies, r.english)}</div>
      <div class="two"><div class="panel"><h3>Best key periods</h3>${table(["Period", "Mean column IC"], periods.map(p => [p.period, p.ic]))}</div>
      <div class="panel"><h3>Kasiski factors</h3>${table(["Factor", "Support"], Object.entries(r.kasiski))}</div></div>
      <div class="panel"><h3>Language fit (if unencrypted)</h3>${table(["Language", "Score"], r.languages.map(l => [l.name, l.score]))}</div>`;
  });
}, "workbench");

route(/^\/translate$/, async () => {
  view().innerHTML = `<h1>Translate</h1><p class="lead">Detects the language, restores word breaks in unspaced cipher output, and translates offline into English.</p>
    <div class="panel"><label for="t">Text, spaced or as continuous letters</label><textarea id="t"></textarea>
    <label for="l">Source language</label><select id="l"><option value="">Detect automatically</option>${Object.entries(state.languages).map(([c, n]) => `<option value="${c}">${esc(n)}</option>`).join("")}</select>
    <button id="go">Translate</button></div><div id="o"></div>`;
  $("#go").onclick = ev => busy(ev.target, $("#o"), async () => {
    const r = await api("/translate", { text: $("#t").value, source: $("#l").value || null });
    $("#o").innerHTML = `<div class="panel"><h3>Language</h3><p>${esc(r.source_name)}</p>${table(["Language", "Fit"], r.detected.map(d => [d.name, d.score]))}
      <h3>With word breaks</h3><pre>${esc(r.spaced)}</pre>
      ${r.translation ? `<h3>English</h3><pre>${esc(r.translation)}</pre>` : ""}${r.note ? `<p class="mute">${esc(r.note)}</p>` : ""}</div>`;
  });
}, "translate");

route(/^\/challenge$/, async () => {
  view().innerHTML = `<h1>Challenge</h1><p class="lead">A hidden system, a random key and a passage from a real book. Use the Workbench to identify it.</p>
    <div class="panel"><button data-l="easy">Easy</button><button data-l="medium">Medium</button><button data-l="hard">Hard</button></div><div id="o"></div>`;
  document.querySelectorAll("[data-l]").forEach(b => b.onclick = ev => busy(ev.target, $("#o"), async () => {
    const c = await api("/challenge/" + b.dataset.l);
    $("#o").innerHTML = `<div class="panel"><h3>Ciphertext (${esc(c.level)})</h3><pre>${esc(c.ciphertext)}</pre>
      <label for="a">Your plaintext</label><textarea id="a"></textarea><button id="chk">Check</button><button id="rev" class="alt">Reveal</button><div id="res"></div></div>`;
    const show = r => `<h3>${esc(r.cipher)}</h3><pre>${esc(JSON.stringify(r.key))}</pre><pre>${esc(r.spaced)}</pre><a href="#/cipher/${esc(r.cipher_id)}">Learn this cipher →</a>`;
    $("#chk").onclick = e => busy(e.target, $("#res"), async () => {
      const r = await api("/challenge/check", { token: c.token, answer: $("#a").value });
      $("#res").innerHTML = r.solved ? `<p class="ok">Solved: ${Math.round(r.accuracy * 100)}% correct.</p>${show(r)}` : `<p>${Math.round(r.accuracy * 100)}% of letters are in the right place. Keep going.</p>`;
    });
    $("#rev").onclick = e => busy(e.target, $("#res"), async () => { $("#res").innerHTML = show(await api("/challenge/check", { token: c.token, reveal: true })); });
  }));
}, "challenge");
