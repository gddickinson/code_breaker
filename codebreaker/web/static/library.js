/* Cipher library and the make / break page for each cipher. */
const SIMS = ["enigma", "lorenz", "jefferson", "scytale", "grille", "railfence", "vigenere", "playfair"];
const FAMILY_ORDER = ["Monoalphabetic", "Polyalphabetic", "Polygraphic", "Fractionating", "Transposition", "Book and homophonic", "Codes", "Scripts", "Music", "Machines", "Modern stream", "Modern symmetric", "Hashes", "Public key"];

route(/^\/$/, async () => {
  const byFam = {};
  state.ciphers.forEach(c => (byFam[c.family] ||= []).push(c));
  view().innerHTML = `<section class="hero"><p class="kicker">// CIPHER_ARCHIVE.ONLINE</p><h1 class="glitch" data-text="Every cipher here can be made and broken">Every cipher here can be made and broken</h1>
    <p class="lead">${state.ciphers.length} systems from Spartan rods to AES. Each page explains how it works, encrypts your own text, and runs a real attack.</p><p><a class="cta" href="#/machine/enigma">Operate the Enigma</a><a class="cta alt" href="#/leads">Open the Lead Board</a><a class="cta" href="#/coverage">Coverage</a></p></section>
    ${FAMILY_ORDER.filter(f => byFam[f]).map(f => `<section class="family"><h2>${esc(f)}</h2><div class="grid">
      ${byFam[f].map(c => `<a class="card" href="#/cipher/${esc(c.id)}"><b>${esc(c.name)}</b><small>${esc(c.era)}</small><span>${esc(c.summary)}</span></a>`).join("")}
    </div></section>`).join("")}`;
}, "library");

route(/^\/cipher\/([\w-]+)$/, async id => {
  const c = await api("/ciphers/" + id);
  const input = p => {
    const v = c.key[p.name] ?? "";
    if (p.kind === "choice") return `<label for="k_${p.name}">${esc(p.label)}</label><select id="k_${p.name}" data-key="${p.name}">${p.choices.map(o => `<option ${o === v ? "selected" : ""}>${esc(o)}</option>`).join("")}</select>`;
    return `<label for="k_${p.name}">${esc(p.label)}</label><input id="k_${p.name}" data-key="${p.name}" value="${esc(v)}">`;
  };
  view().innerHTML = `<a href="#/">← Library</a>
    <h1>${esc(c.name)}</h1>
    <p><span class="tag">${esc(c.family)}</span><span class="tag">${esc(c.era)}</span></p>
    <p class="lead">${esc(c.summary)}</p>
    ${SIMS.includes(c.id) ? `<p><a href="#/machine/${c.id === "railfence" ? "rail" : c.id}">Operate a working model →</a></p>` : ""}
    <h2>How it works</h2><p>${esc(c.how)}</p>
    <h2>Worked example</h2>
    <div class="panel">
      <h3>Message</h3><pre>${esc(c.example)}</pre>
      ${Object.keys(c.key).length ? `<h3>Key</h3><pre>${esc(JSON.stringify(c.key))}</pre>` : ""}
      <h3>Result</h3><pre>${esc(c.example_cipher)}</pre>${c.family === "Music" ? musicPanel(c.example_cipher, "playEx") : ""}
      ${c.example_back !== null ? `<h3>Decrypted again</h3><pre>${esc(c.example_back)}</pre>` : `<p class="mute">One-way: there is no decryption.</p>`}
    </div>
    <h2>Try it yourself</h2>
    <div class="panel">
      <div class="row">${c.params.map(input).join("") ? c.params.map(p => `<div>${input(p)}</div>`).join("") : '<p class="mute">This system has no key.</p>'}</div>
      <label for="txt">Text</label><textarea id="txt">${esc(c.example)}</textarea>
      <button id="enc">Encrypt</button>${c.example_back !== null ? '<button id="dec" class="alt">Decrypt</button>' : ""}
      <div id="out"></div>
    </div>
    <h2>How it breaks</h2><p>${esc(c.weakness)}</p>
    <div class="panel">
      ${c.can_attack ? `<p>${c.modern ? "Runs a real attack on a local toy target." : `Encrypts a test passage with a random key, then recovers it. Method: ${esc(c.attack_name)}.`}</p>
      <button id="atk">Run the attack</button><div id="atkout"></div>` : "<p>No attack demonstration.</p>"}
      ${c.paste_attack ? `<h3>Break your own ciphertext</h3><label for="ct">Ciphertext</label><textarea id="ct"></textarea><label for="sl">Plaintext language</label>${langSelect("sl")}<button id="solve" class="alt">Break it</button><div id="solveout"></div>` : ""}
    </div>`;

  const keyVals = () => Object.fromEntries([...document.querySelectorAll("[data-key]")].map(e => [e.dataset.key, e.value]));
  const runOp = op => async ev => {
    const out = $("#out");
    await busy(ev.target, out, async () => {
      const r = await api(`/ciphers/${id}/run`, { op, text: $("#txt").value, key: keyVals() });
      out.innerHTML = `<h3>Output</h3><pre>${esc(r.output)}</pre>${c.family === "Music" && op === "encrypt" ? musicPanel(r.output, "playOut") : ""}`;
      if ($("#playOut")) $("#playOut").onclick = () => musicPlay(r.output);
    });
  };
  $("#enc").onclick = runOp("encrypt");
  if ($("#playEx")) $("#playEx").onclick = () => musicPlay(c.example_cipher);
  if ($("#dec")) $("#dec").onclick = runOp("decrypt");
  if ($("#atk")) $("#atk").onclick = ev => busy(ev.target, $("#atkout"), async () => {
    const r = await api(`/ciphers/${id}/attack`, {});
    $("#atkout").innerHTML = r.kind === "modern" ? `<h3>${esc(r.title)}</h3><ol class="steps">${r.steps.map(s => `<li>${esc(s)}</li>`).join("")}</ol>
        <p>${r.success ? '<span class="tag good">Attack succeeded</span>' : '<span class="tag bad">Attack failed</span>'}</p>
        <h3>Recovered</h3><pre>${esc(r.recovered)}</pre><h3>Actual</h3><pre>${esc(r.truth)}</pre>`
      : `<p><span class="tag ${r.accuracy > .9 ? "good" : "warn"}">${Math.round(r.accuracy * 100)}% of letters recovered</span></p>
        <h3>Secret key</h3><pre>${esc(JSON.stringify(r.secret_key))}</pre><h3>Ciphertext</h3><pre>${esc(String(r.ciphertext).slice(0, 400))}</pre>
        <h3>Key found</h3><pre>${esc(JSON.stringify(r.key).slice(0, 500))}</pre><h3>Plaintext recovered</h3><pre>${esc(r.plaintext)}</pre><p class="mute">${esc(r.method)}</p>`;
  });
  if ($("#solve")) $("#solve").onclick = ev => busy(ev.target, $("#solveout"), async () => {
    const r = await api(`/ciphers/${id}/solve`, { text: $("#ct").value, lang: $("#sl").value });
    $("#solveout").innerHTML = `<h3>Best reading</h3><pre>${esc(r.spaced)}</pre><p class="mute">${esc(r.method)}. Score ${esc(r.score)}: closer to −4 reads more like real text.</p>
      <h3>Key</h3><pre>${esc(JSON.stringify(r.key).slice(0, 500))}</pre>`;
  });
}, "library");

const PLANNED = ["Purple", "SIGABA", "Typex", "Ragbaby", "Bazeries", "Portax", "Pollux", "Morbit", "Cadenus", "Swagman", "Digrafid", "Tri-square", "Phillips", "Nomenclators", "Post-quantum toy (LWE)"];
route(/^\/coverage$/, async () => {
  const fam = {};
  state.ciphers.forEach(c => (fam[c.family] ||= []).push(c));
  const items = FAMILY_ORDER.filter(f => fam[f]).map(f => ({ label: f, value: fam[f].length, hit: false }));
  view().innerHTML = `<p class="kicker">// COVERAGE</p><h1>What is covered</h1><p class="lead">${state.ciphers.length} systems so far. The list of everything ever invented is open-ended, so this page shows what exists and what is planned next.</p>
    ${barChart({ title: "Systems implemented, by family", items, unit: "systems" })}
    <h2>Planned next</h2><ul>${PLANNED.map(p => `<li>${esc(p)}</li>`).join("")}</ul>`;
}, "library");
