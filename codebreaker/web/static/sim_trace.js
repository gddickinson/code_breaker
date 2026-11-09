/* Letter-by-letter visual traces for the rail fence, Vigenere and Playfair ciphers. */
function stepper(pos, max, draw) {
  const set = v => { pos.i = Math.max(0, Math.min(max(), v)); draw(); };
  $("#prev").onclick = () => set(pos.i - 1);
  $("#next").onclick = () => set(pos.i + 1);
}

route(/^\/machine\/rail$/, async () => {
  view().innerHTML = `${backLink}<h1>Rail fence</h1><p class="lead">Letters bounce down and up across the rails, and the ciphertext is read one rail at a time.</p>
    <div class="panel"><label for="m">Message</label><input id="m" value="WE ARE DISCOVERED FLEE AT ONCE"><label for="k">Rails: <b id="v"></b></label><input id="k" type="range" min="2" max="8" value="3"></div>
    <div class="panel scroll"><div id="g"></div><h3>Ciphertext</h3><pre id="o"></pre></div>`;
  const draw = () => {
    const t = clean($("#m").value), k = +$("#k").value, pat = railPattern(t.length, k);
    $("#v").textContent = k;
    $("#g").innerHTML = `<table class="tight"><tbody>${[...Array(k).keys()].map(r => `<tr>${[...t].map((c, i) => `<td class="cell" style="color:${HUE[r % HUE.length]}">${pat[i] === r ? c : ""}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
    $("#o").textContent = [...Array(k).keys()].map(r => [...t].filter((_, i) => pat[i] === r).join("")).join("");
  };
  $("#m").oninput = draw; $("#k").oninput = draw; draw();
}, "machines");

route(/^\/machine\/vigenere$/, async () => {
  view().innerHTML = `${backLink}<h1>Vigenere tableau</h1><p class="lead">The key letter chooses the row and the message letter chooses the column. The ciphertext letter is where they cross.</p>
    <div class="panel"><div class="row"><div><label for="m">Message</label><input id="m" value="ATTACK AT DAWN"></div><div><label for="k">Keyword</label><input id="k" value="LEMON"></div></div><button id="prev" class="alt">Previous</button><button id="next">Next letter</button></div>
    <div class="panel"><p id="n"></p><pre id="o"> </pre><div id="g" class="scroll"></div></div>`;
  const pos = { i: 0 };
  const trace = () => clean($("#k").value) && clean($("#m").value) ? vigenereTrace($("#m").value, $("#k").value) : [];
  const draw = () => {
    const tr = trace();
    if (!tr.length) { $("#n").textContent = "Enter a message and a keyword."; $("#g").innerHTML = ""; return; }
    const s = tr[Math.min(pos.i, tr.length - 1)], col = idx(s.p), row = idx(s.k);
    $("#n").textContent = `Letter ${Math.min(pos.i, tr.length - 1) + 1}: message ${s.p}, key ${s.k}, ciphertext ${s.c}.`;
    $("#o").textContent = tr.slice(0, pos.i + 1).map(x => x.c).join("");
    $("#g").innerHTML = `<table class="tight tableau"><thead><tr><th></th>${[...AZ].map((c, j) => `<th class="${j === col ? "hit" : ""}">${c}</th>`).join("")}</tr></thead><tbody>${[...AZ].map((c, r) => `<tr><th class="${r === row ? "hit" : ""}">${c}</th>${[...AZ].map((_, j) => `<td class="${r === row && j === col ? "cross" : r === row || j === col ? "line" : ""}">${AZ[(r + j) % 26]}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  };
  stepper(pos, () => trace().length - 1, draw);
  $("#m").oninput = () => { pos.i = 0; draw(); }; $("#k").oninput = () => { pos.i = 0; draw(); }; draw();
}, "machines");

route(/^\/machine\/playfair$/, async () => {
  view().innerHTML = `${backLink}<h1>Playfair square</h1><p class="lead">The message is split into pairs, and each pair moves by one of three rules.</p>
    <div class="panel"><div class="row"><div><label for="m">Message</label><input id="m" value="HIDE THE GOLD UNDER THE OLD STUMP"></div><div><label for="k">Keyword</label><input id="k" value="PLAYFAIR"></div></div><button id="prev" class="alt">Previous</button><button id="next">Next pair</button></div>
    <div class="panel center"><div id="g"></div><p id="n"></p><pre id="o"> </pre></div>`;
  const pos = { i: 0 };
  const pairs = () => playfairPairs($("#m").value);
  const draw = () => {
    const sq = playfairSquare($("#k").value), p = pairs();
    if (!p.length) { $("#n").textContent = "Enter a message."; return; }
    const at = Math.min(pos.i, p.length - 1), [a, b] = p[at], s = playfairStep(sq, a, b);
    $("#g").innerHTML = `<table class="grille"><tbody>${[0, 1, 2, 3, 4].map(r => `<tr>${[0, 1, 2, 3, 4].map(c => { const i = r * 5 + c; return `<td class="${s.from.includes(i) ? "hole" : s.to.includes(i) ? "target" : ""}">${sq[i]}</td>`; }).join("")}</tr>`).join("")}</tbody></table>`;
    $("#n").textContent = `Pair ${a}${b} becomes ${s.out}. ${s.rule}`;
    $("#o").textContent = p.slice(0, at + 1).map(([x, y]) => playfairStep(sq, x, y).out).join(" ");
  };
  stepper(pos, () => pairs().length - 1, draw);
  $("#m").oninput = () => { pos.i = 0; draw(); }; $("#k").oninput = () => { pos.i = 0; draw(); }; draw();
}, "machines");
