/* First Contact lab (Round 84): is a stream of symbols language-like, can a bit stream be laid out as a picture,
   and how could a message be designed for a stranger. */
let fcGrid = { w: 17, h: 29, cells: [] };

function fcDraw(canvas, rows, scale = 8) {
  const h = rows.length, w = rows[0].length, g = canvas.getContext("2d");
  canvas.width = w * scale; canvas.height = h * scale;
  g.fillStyle = "#0f0d1f"; g.fillRect(0, 0, canvas.width, canvas.height);
  g.fillStyle = "#00f0ff";
  rows.forEach((r, y) => [...r].forEach((b, x) => { if (b === "1") g.fillRect(x * scale, y * scale, scale - 1, scale - 1); }));
}

function fcProfileRow(name, p) {
  return [name, p.alphabet, p.H1, `${p.H2} (shuffled ${p.H2_shuffled})`, p.z_H2, p.z_repeat4, p.zipf_slope];
}

async function fcLayout(bits, canvas, out) {
  const r = await api("/contact/layout", { text: bits });
  fcDraw(canvas, r.grid, Math.max(3, Math.min(10, Math.floor(420 / r.best_width))));
  out.innerHTML = `<p>${r.length} bits; factors ${r.factors.length ? esc(r.factors.join(", ")) : "none (prime: every width tried)"}. Best width <b>${r.best_width}</b> (${r.rows} rows), z=${r.z} against shuffled bits: ${r.picture ? "<b>a picture</b> (random bits stayed under z=2.1)" : "no clear picture"}.</p>
    ${table(["Width", "Rows agree beyond chance"], r.ranking.map(x => [x.width, x.score]))}`;
}

function fcEditor() {
  const c = $("#fcDesign"), s = 14, { w, h } = fcGrid;
  if (fcGrid.cells.length !== w * h) fcGrid.cells = Array(w * h).fill(0);
  c.width = w * s; c.height = h * s;
  const g = c.getContext("2d");
  g.fillStyle = "#0f0d1f"; g.fillRect(0, 0, c.width, c.height);
  fcGrid.cells.forEach((v, i) => { g.fillStyle = v ? "#ff2a6d" : "#1d1a33"; g.fillRect((i % w) * s, Math.floor(i / w) * s, s - 1, s - 1); });
  c.onclick = e => { const r = c.getBoundingClientRect(), x = Math.floor((e.clientX - r.left) * c.width / r.width / s), y = Math.floor((e.clientY - r.top) * c.height / r.height / s); fcGrid.cells[y * w + x] ^= 1; fcEditor(); };
}

route(/^\/contact$/, async () => {
  const ref = await api("/contact/references");
  view().innerHTML = `<p class="kicker">// FIRST CONTACT</p><h1>First Contact lab</h1>
    <p class="lead">How would we read a message from someone with no shared language: a new script, an animal, an intelligent machine, another world? The first questions are whether a signal has structure at all, and whether it carries a picture. This page measures both, with controls, and lets you design a message a stranger could decode.</p>
    <h2>Is it language-like?</h2><div class="panel"><p>Language has sequential structure: the next symbol depends on the ones before, far more than in a shuffled copy. So do birdsong, music and machine codes, so structure is necessary for language but not proof of it. Reference streams, measured the same way:</p>
      ${table(["Stream", "Alphabet", "H1 bits", "H2 bits (next given one)", "z (H2 vs shuffled)", "z (repeated 4-grams)", "Zipf slope"], Object.entries(ref.references).map(([k, v]) => fcProfileRow(k, v)))}
      <p class="mute">H1: entropy of single symbols. H2: entropy of the next symbol given the previous one; lower than shuffled means order matters. Zipf slope: about -1 for words of human languages. Voynich and rongorongo are undeciphered: their structure says nothing about meaning.</p>
      <label for="fcText">Your symbols (characters, or units separated by spaces)</label><textarea id="fcText" rows="4"></textarea><button id="fcGo">Measure</button><div id="fcOut" aria-live="polite"></div></div>
    <h2>The Arecibo message (1974)</h2><div class="panel"><p>Sent once from the Arecibo radio telescope: 1,679 bits. 1,679 is 23 x 73, a product of two primes, so a receiver who factors it has only two ways to lay it out. The decoder tries every width and keeps the one where rows agree with the rows above them.</p>
      <button id="fcArec">Decode the message</button><div class="row"><div><canvas id="fcArecC" style="image-rendering:pixelated;max-width:100%"></canvas></div><div id="fcArecOut"></div></div>
      <p class="mute">Bits from the Wikipedia article on the Arecibo message (saved in this project). In controls, drawn pictures of 17x29 to 13x61 were laid out at the right width every time; random bits never exceeded z=2.1.</p></div>
    <h2>Design a message</h2><div class="panel"><p>Draw on a grid whose sides are primes, as Arecibo's were; the message is sent as one line of bits, and the decoder must find your picture without being told the size.</p>
      <div class="row"><div><label for="fcW">Width</label><select id="fcW">${[11, 13, 17, 19, 23].map(n => `<option ${n === 17 ? "selected" : ""}>${n}</option>`).join("")}</select></div><div><label for="fcH">Height</label><select id="fcH">${[19, 23, 29, 31, 37].map(n => `<option ${n === 29 ? "selected" : ""}>${n}</option>`).join("")}</select></div></div>
      <canvas id="fcDesign" style="cursor:crosshair;max-width:100%"></canvas>
      <div><button id="fcSend">Send it as bits</button> <button class="alt" id="fcClear">Clear</button></div>
      <div class="row"><div><canvas id="fcRecv" style="image-rendering:pixelated;max-width:100%"></canvas></div><div id="fcRecvOut"></div></div></div>
    <h2>From structure to meaning</h2><div class="panel"><p>Finding structure is the easy part. Meaning needs something shared: a bilingual text (the Rosetta Stone), known names (Linear B was read through place names), events the signals go with (animal calls studied by playing them back and watching the response), or physics and mathematics, which any technological sender must share. That is why messages like Arecibo begin with counting. Machine methods can also align two languages' patterns of word use without a dictionary, but only where the two minds carve up a similar world.</p></div>`;
  $("#fcGo").onclick = ev => busy(ev.target, $("#fcOut"), async () => {
    const p = await api("/contact/profile", { text: $("#fcText").value });
    $("#fcOut").innerHTML = `${table(["Stream", "Alphabet", "H1 bits", "H2 bits (next given one)", "z (H2 vs shuffled)", "z (repeated 4-grams)", "Zipf slope"], [fcProfileRow("Yours", p)])}<p><b>${esc(p.verdict)}</b>.</p>`;
  });
  $("#fcArec").onclick = ev => busy(ev.target, $("#fcArecOut"), async () => { const a = await api("/contact/arecibo"); await fcLayout(a.bits, $("#fcArecC"), $("#fcArecOut")); });
  const resize = () => { fcGrid = { w: +$("#fcW").value, h: +$("#fcH").value, cells: [] }; fcEditor(); };
  $("#fcW").onchange = resize; $("#fcH").onchange = resize; $("#fcClear").onclick = resize;
  $("#fcSend").onclick = ev => busy(ev.target, $("#fcRecvOut"), async () => {
    if (fcGrid.cells.filter(Boolean).length < 5) throw new Error("Draw something first (a few cells at least).");
    await fcLayout(fcGrid.cells.join(""), $("#fcRecv"), $("#fcRecvOut"));
    $("#fcRecvOut").insertAdjacentHTML("beforeend", `<p>${+$("#fcW").value === +($("#fcRecvOut").querySelector("b")?.textContent || 0) ? "Decoded at your width." : "Not decoded at your width: try a picture with more structure (lines, shapes) and fewer isolated dots."}</p>`);
  });
  resize();
}, "contact");
