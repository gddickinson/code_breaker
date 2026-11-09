/* Simulations of computer cryptography: AES, ECB leakage, avalanche, Feistel, key exchange, RSA, Colossus. */
const CK = Uint8Array.from([...Array(16).keys()]);
const heat = v => `hsl(${(v * 1.4 + 180) % 360} 75% ${28 + v / 12}%)`;
const stateGrid = (s, cmp) => `<div class="aesgrid">${[0, 1, 2, 3].map(r => [0, 1, 2, 3].map(c => { const i = c * 4 + r; return `<div style="background:${heat(s[i])}" class="${cmp && cmp[i] !== s[i] ? "chg" : ""}">${s[i].toString(16).padStart(2, "0")}</div>`; }).join("")).join("")}</div>`;
const OPS = { AddRoundKey: "Each byte is XORed with the round key.", SubBytes: "Each byte is replaced using a fixed non-linear table.", ShiftRows: "Rows slide left by 0, 1, 2 and 3 places.", MixColumns: "Each column is mixed so every byte affects four." };

route(/^\/how\/aes$/, async () => {
  view().innerHTML = `${howBack}<h1>Inside AES</h1><p class="lead">AES-128 turns 16 bytes through ten rounds of four simple steps. This is real AES, and its output matches a standard library.</p>
    <div class="panel"><label for="m">16 characters</label><input id="m" value="Attack at dawn!!" maxlength="16"><label for="s">Step: <b id="v"></b></label><input id="s" type="range" min="0" value="0"><button id="play">Play</button><div class="center" id="g"></div><p id="d"></p><h3>Ciphertext</h3><pre id="o"></pre></div>`;
  let timer = null, tr = [];
  const build = () => { const b = [...$("#m").value.padEnd(16, " ")].slice(0, 16).map(c => c.charCodeAt(0) & 255); tr = aesTrace(b, CK); $("#s").max = tr.length - 1; draw(); };
  const draw = () => { const i = +$("#s").value, t = tr[i]; $("#v").textContent = `${i + 1} of ${tr.length}: round ${t.round}, ${t.op}`; $("#g").innerHTML = stateGrid(t.state, tr[i - 1]?.state); $("#d").textContent = OPS[t.op]; $("#o").textContent = hex(tr.at(-1).state); };
  $("#m").oninput = build; $("#s").oninput = draw;
  $("#play").onclick = () => { clearInterval(timer); $("#s").value = 0; timer = setInterval(() => { if (!location.hash.endsWith("/how/aes") || +$("#s").value >= tr.length - 1) return clearInterval(timer); $("#s").value = +$("#s").value + 1; draw(); }, 550); };
  build();
}, "how");

route(/^\/how\/ecb$/, async () => {
  view().innerHTML = `${howBack}<h1>The ECB picture</h1><p class="lead">AES is strong, but ECB mode encrypts each block separately, so identical blocks of pixels stay identical. Chaining with CBC hides the shapes.</p>
    <div class="panel"><div class="three">${[["a", "Original"], ["b", "AES-ECB"], ["c", "AES-CBC"]].map(([i, l]) => `<figure><canvas id="${i}" width="256" height="256" role="img" aria-label="${l} image"></canvas><figcaption>${l}</figcaption></figure>`).join("")}</div></div>`;
  const s = 256, src = $("#a").getContext("2d");
  src.fillStyle = "#1b2a5a"; src.fillRect(0, 0, s, s); src.fillStyle = "#00f0ff"; src.beginPath(); src.arc(128, 118, 72, 0, 7); src.fill(); src.fillStyle = "#1b2a5a"; src.fillRect(104, 92, 48, 72); src.fillStyle = "#ff2a6d"; src.fillRect(36, 206, 184, 20); src.fillStyle = "#f5e642"; src.fillRect(62, 30, 22, 22); src.fillRect(172, 30, 22, 22);
  const data = src.getImageData(0, 0, s, s).data, bytes = new Uint8Array(s * s * 3);
  for (let i = 0, j = 0; i < data.length; i += 4) { bytes[j++] = data[i]; bytes[j++] = data[i + 1]; bytes[j++] = data[i + 2]; }
  const paint = (id, out) => { const g = $("#" + id).getContext("2d"), im = g.createImageData(s, s); for (let i = 0, j = 0; i < im.data.length; i += 4) { im.data[i] = out[j++]; im.data[i + 1] = out[j++]; im.data[i + 2] = out[j++]; im.data[i + 3] = 255; } g.putImageData(im, 0, 0); };
  const ecb = new Uint8Array(bytes), cbc = new Uint8Array(bytes);
  let prev = Array(16).fill(37);
  const memo = new Map();
  for (let b = 0; b + 16 <= bytes.length; b += 16) {
    const block = bytes.slice(b, b + 16), k = block.join();
    if (!memo.has(k)) memo.set(k, aesEncrypt([...block], CK));
    ecb.set(memo.get(k), b);
    prev = aesEncrypt([...block].map((v, i) => v ^ prev[i]), CK);
    cbc.set(prev, b);
  }
  paint("b", ecb); paint("c", cbc);
}, "how");

route(/^\/how\/avalanche$/, async () => {
  const base = [...new TextEncoder().encode("Sixteen byte msg")];
  let flip = 0;
  view().innerHTML = `${howBack}<h1>The avalanche effect</h1><p class="lead">In a good cipher, changing one input bit changes about half of all output bits. That means no small change leaves a visible trace.</p>
    <div class="panel"><label for="b">Input bit to flip: <b id="v"></b></label><input id="b" type="range" min="0" max="127" value="0"><div id="g" class="bitgrid"></div><p id="n"></p></div>`;
  const bits = a => a.flatMap(v => [...Array(8).keys()].map(i => (v >> (7 - i)) & 1));
  const draw = () => {
    flip = +$("#b").value; $("#v").textContent = flip;
    const m = [...base]; m[flip >> 3] ^= 128 >> (flip & 7);
    const x = bits(aesEncrypt(base, CK)), y = bits(aesEncrypt(m, CK)), diff = x.map((v, i) => v !== y[i]);
    $("#g").innerHTML = diff.map(d => `<i class="${d ? "on" : ""}"></i>`).join("");
    $("#n").textContent = `${diff.filter(Boolean).length} of 128 output bits changed. Lit squares are bits that differ.`;
  };
  $("#b").oninput = draw; draw();
}, "how");

route(/^\/how\/feistel$/, async () => {
  view().innerHTML = `${howBack}<h1>A Feistel network</h1><p class="lead">DES splits a block in half and scrambles one half using the other. Simplified DES shows the same structure in eight bits.</p>
    <div class="panel"><div class="row"><div><label for="v">Input byte (0-255)</label><input id="v" type="number" min="0" max="255" value="179"></div><div><label for="k">Key (0-1023)</label><input id="k" type="number" min="0" max="1023" value="642"></div></div><div id="g"></div></div>`;
  const draw = () => {
    const r = sdesTrace(Math.min(255, Math.max(0, +$("#v").value || 0)), Math.min(1023, Math.max(0, +$("#k").value || 0)));
    $("#g").innerHTML = r.steps.map(([n, b]) => `<div class="feistel"><small>${esc(n)}</small><div>${b.map((x, i) => `<span class="${x ? "on" : ""} ${i === 3 ? "gap" : ""}">${x}</span>`).join("")}</div></div>`).join("") + `<p>Ciphertext byte: <b>${r.out}</b></p>`;
  };
  $("#v").oninput = draw; $("#k").oninput = draw; draw();
}, "how");

route(/^\/how\/dh$/, async () => {
  const p = 23, g = 5, pow = (b, e) => { let r = 1; for (let i = 0; i < e; i++) r = r * b % p; return r; };
  view().innerHTML = `${howBack}<h1>Key exchange on a clock</h1><p class="lead">Numbers wrap around a clock of ${p} hours. Each side keeps a secret and publishes only where it lands. Both then reach the same shared hour.</p>
    <div class="panel"><div class="row"><div><label for="a">Alice's secret: <b id="av"></b></label><input id="a" type="range" min="1" max="21" value="6"></div><div><label for="b">Bob's secret: <b id="bv"></b></label><input id="b" type="range" min="1" max="21" value="15"></div></div><div class="center" id="g"></div><div id="t"></div></div>`;
  const P = h => { const t = h / p * 2 * Math.PI; return [170 + 128 * Math.sin(t), 170 - 128 * Math.cos(t)]; };
  const draw = () => {
    const a = +$("#a").value, b = +$("#b").value, A = pow(g, a), B = pow(g, b), S = pow(A, b); $("#av").textContent = a; $("#bv").textContent = b;
    const mark = (h, label, col, dy) => { const [x, y] = P(h); return `<circle cx="${x}" cy="${y}" r="12" fill="${col}"/><text x="${x}" y="${y + 4}" text-anchor="middle" class="clockv">${h}</text><text x="${x}" y="${y + dy}" text-anchor="middle" class="axisl">${label}</text>`; };
    $("#g").innerHTML = `<svg class="disk" viewBox="0 0 340 340" role="img" aria-label="Modular clock showing public values and the shared secret"><circle cx="170" cy="170" r="128" fill="none" stroke="var(--line)"/>${[...Array(p).keys()].map(h => `<circle cx="${P(h)[0]}" cy="${P(h)[1]}" r="2.5" fill="var(--mute)"/>`).join("")}${mark(A, "Alice public", "var(--c1)", -18)}${mark(B, "Bob public", "var(--c4)", 28)}${mark(S, "Shared", "var(--c2)", -18)}</svg>`;
    $("#t").innerHTML = table(["", "Computation", "Result"], [["Alice publishes", `${g}^${a} mod ${p}`, A], ["Bob publishes", `${g}^${b} mod ${p}`, B], ["Alice computes", `${B}^${a} mod ${p}`, pow(B, a)], ["Bob computes", `${A}^${b} mod ${p}`, pow(A, b)]]);
  };
  $("#a").oninput = draw; $("#b").oninput = draw; draw();
}, "how");

route(/^\/how\/rsa$/, async () => {
  const n = 3233, e = 17, d = 2753;
  view().innerHTML = `${howBack}<h1>RSA arithmetic</h1><p class="lead">RSA raises numbers to huge powers. Square-and-multiply needs one step per bit, so it stays fast. This uses the tiny key n = 61 × 53.</p>
    <div class="panel"><label for="m">Message number (2-3000): <b id="v"></b></label><input id="m" type="range" min="2" max="3000" value="65"><div id="t"></div></div>`;
  const draw = () => {
    const m = +$("#m").value; $("#v").textContent = m;
    const enc = modPowSteps(m, e, n), dec = modPowSteps(enc.value, d, n);
    $("#t").innerHTML = `<h3>Encrypt: ${m}^${e} mod ${n}. Exponent bits ${enc.bits}</h3>${table(["Bit", "After squaring", "After multiply"], enc.steps.map(s => [s.bit, s.squared, s.value]))}<p>Ciphertext: <b>${enc.value}</b></p><h3>Decrypt with d = ${d}</h3><p>${dec.steps.length} steps give back <b>${dec.value}</b>.</p>`;
  };
  $("#m").oninput = draw; draw();
}, "how");

route(/^\/how\/colossus$/, async () => {
  const { sizes, wheels } = await api("/machines/lorenz");
  const w = wheels[0], size = sizes[0], truth = Math.floor(Math.random() * size), tape = colossusTape(w, truth, 2400, 0.62, 41 + truth);
  view().innerHTML = `${howBack}<h1>Colossus</h1><p class="lead">Colossus ran a paper tape past each wheel setting and counted agreements. German text is slightly non-random, so the right setting scores a little higher. This is a simplified teaching model of that one idea.</p>
    <div class="panel"><button id="go">Run the tape</button><p id="st" class="mute">Each bar is one of ${size} wheel starts.</p><svg class="chart" id="c" viewBox="0 0 900 220" role="img" aria-label="Agreement count for each wheel start"></svg></div>`;
  const all = colossusCount(tape, w), lo = Math.min(...all), hi = Math.max(...all), bw = 860 / size;
  const draw = shown => { $("#c").innerHTML = `<text x="10" y="18" class="charttitle">Agreements with the tape</text>${all.map((v, i) => { const s = i < shown, h = s ? 20 + (v - lo) / (hi - lo || 1) * 160 : 2; return `<rect x="${20 + i * bw}" y="${205 - h}" width="${bw - 3}" height="${h}" rx="3" fill="${s && v === hi ? "var(--c2)" : "var(--c1)"}"><title>Start ${i}: ${s ? v : "not run"} agreements</title></rect>`; }).join("")}`; };
  draw(0);
  $("#go").onclick = () => { let i = 0; const t = setInterval(() => { if (!location.hash.endsWith("/how/colossus")) return clearInterval(t); i++; draw(i); if (i >= size) { clearInterval(t); const f = all.indexOf(hi); $("#st").textContent = `Highest count at start ${f}. ${f === truth ? "That is the true setting." : `The true setting was ${truth}.`}`; } }, 70); };
}, "how");
