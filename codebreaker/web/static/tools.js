/* Workbench (analysis), Challenge and Translate pages. */
function freqBars(obs, exp) {
  const keys = Object.keys(obs);
  const max = Math.max(...keys.map(k => Math.max(obs[k], exp[k])), 1);
  return `<div class="bars" role="img" aria-label="Letter counts compared with expected English">${keys.map(k => `<div class="bar" title="${k}: ${obs[k]} seen, ${exp[k]} expected in English"><i style="height:${obs[k] / max * 100}%"></i><u style="bottom:${exp[k] / max * 100}%"></u></div>`).join("")}</div>
    <div class="axis">${keys.map(k => `<span>${k}</span>`).join("")}</div><p class="mute">Bars show your text. Lines show the English expectation.</p>`;
}

route(/^\/workbench$/, async () => {
  view().innerHTML = `<h1>Workbench</h1><p class="lead">Paste any ciphertext. Crack it runs every method available and shows each stage, or save it for the hunter to keep working on.</p>
    <div class="panel"><label for="t">Ciphertext</label><textarea id="t"></textarea>
    <div class="row crackopts"><div><label for="cb">Time allowed</label><select id="cb"><option value="15">15 seconds</option><option value="45" selected>45 seconds</option><option value="120">2 minutes</option></select></div>
    <div><label for="cl">Language</label><select id="cl"><option value="">Try all six</option><option value="en">English</option><option value="fr">French</option><option value="de">German</option><option value="it">Italian</option><option value="es">Spanish</option><option value="la">Latin</option></select></div></div>
    <button id="crack">Crack it</button><button id="stop" class="alt" disabled>Stop</button><button id="go" class="alt">Statistics only</button></div>
    <div id="abo"></div><div id="o"></div>${submitPanel()}`;
  try { const handed = sessionStorage.getItem("workbenchText"); if (handed) { $("#t").value = handed; sessionStorage.removeItem("workbenchText"); } } catch (e) { /* storage unavailable */ }
  crackSetup();
  if (window.PENDING_TEXT) { $("#t").value = window.PENDING_TEXT; window.PENDING_TEXT = null; }
  submitSetup();
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
  const langs = await api("/translate/languages");
  view().innerHTML = `<h1>Translate</h1><p class="lead">Identifies the language among ${langs.length} and translates offline into English. Unspaced capital letters, as a decrypted cipher gives them, get their word breaks restored first.</p>
    <div class="panel"><label for="t">Text, spaced or as continuous letters</label><textarea id="t"></textarea>
    <label for="l">Source language</label><select id="l"><option value="">Detect automatically</option>${langs.map(x => `<option value="${x.code}">${esc(x.name)}${x.translator ? "" : " (no translator yet)"}</option>`).join("")}</select>
    <button id="go">Translate</button></div><div id="o"></div>`;
  $("#go").onclick = ev => busy(ev.target, $("#o"), async () => {
    const r = await api("/translate", { text: $("#t").value, source: $("#l").value || null });
    const rows = r.detected.map(d => [d.name, d.p != null ? `${Math.round(d.p * 100)}%` : d.score]);
    const close = !$("#l").value && r.detected.length > 1 && r.detected[1].p != null && r.detected[1].p > 0.2
      ? `<p class="err">Close call: ${esc(r.detected[0].name)} or ${esc(r.detected[1].name)}. Short texts in related languages are hard to tell apart; choose the language above if this is wrong.</p>` : "";
    $("#o").innerHTML = `<div class="panel"><h3>Language</h3><p>${esc(r.source_name)}</p>${close}${table(["Language", "Fit"], rows)}
      ${r.spaced !== $("#t").value ? `<h3>With word breaks</h3><pre>${esc(r.spaced)}</pre>` : ""}
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
