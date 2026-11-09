/* Working models: Scytale, Alberti disk, Jefferson wheel, turning grille and Lorenz. */
const clean = t => t.toUpperCase().replace(/[^A-Z]/g, "");
const backLink = '<a href="#/machines">← Machines</a>';
const HUE = ["#00f0ff", "#ff2a6d", "#f5e642", "#39ff88", "#b388ff", "#ff9e40"];

route(/^\/machines$/, async () => {
  const M = [["enigma", "Enigma I", "Three moving rotors, a reflector and a plugboard, with the current drawn live."], ["bombe", "Bletchley bombe", "Break a plugboard Enigma from a known word, by contradiction."], ["lorenz", "Lorenz teleprinter model", "Ten pin wheels produce a five-bit key stream."], ["jefferson", "Jefferson wheel", "A stack of lettered discs. Dial a line and send another."],
    ["alberti", "Alberti cipher disk", "Two concentric alphabets, from 1467. Turn the inner ring."], ["scytale", "Spartan scytale", "Wind a strip round a rod and write along it."], ["grille", "Turning grille", "A holed card, rotated four times."], ["rail", "Rail fence", "Watch a message zigzag across the rails."],
    ["vigenere", "Vigenere tableau", "Follow each letter through the square table."], ["playfair", "Playfair square", "See the row, column and rectangle rules applied."]];
  view().innerHTML = `<h1>Machines and mechanisms</h1><p class="lead">Working models you can operate. Each uses the same algorithm as the matching cipher in the Library.</p><div class="grid">${M.map(([id, n, d]) => `<a class="card" href="#/machine/${id}"><b>${n}</b><span>${d}</span></a>`).join("")}</div>`;
}, "machines");

route(/^\/machine\/scytale$/, async () => {
  view().innerHTML = `${backLink}<h1>Spartan scytale</h1><p class="lead">The strip winds around the rod, so letters that touch along the rod end up far apart on the strip.</p>
    <div class="panel"><label for="m">Message</label><input id="m" value="SEND MORE SPEARS TO SPARTA"><label for="k">Rod thickness: <b id="kv"></b> letters per turn</label><input id="k" type="range" min="2" max="9" value="4"></div>
    <div class="panel"><h3>Letters along the rod, each colour is one winding of the strip</h3><div id="rod" class="scroll"></div><h3>Unwound strip (ciphertext)</h3><div id="strip" class="strip"></div></div>`;
  const draw = () => {
    const t = clean($("#m").value), k = +$("#k").value;
    $("#kv").textContent = k;
    const rows = Math.ceil(t.length / k);
    let cells = "";
    for (let r = 0; r < rows; r++) cells += `<tr>${[...Array(k).keys()].map(c => `<td class="cell" style="color:${HUE[c % HUE.length]}">${t[r * k + c] || ""}</td>`).join("")}</tr>`;
    $("#rod").innerHTML = `<table class="tight"><tbody>${cells}</tbody></table>`;
    $("#strip").innerHTML = [...Array(k).keys()].map(c => [...t.slice(c).matchAll(new RegExp(`(.)(?:.{${k - 1}})?`, "g"))].map(m => `<span style="color:${HUE[c % HUE.length]}">${m[1]}</span>`).join("")).join("");
  };
  $("#m").oninput = draw; $("#k").oninput = draw; draw();
}, "machines");

route(/^\/machine\/alberti$/, async () => {
  view().innerHTML = `${backLink}<h1>Alberti cipher disk</h1><p class="lead">Leon Battista Alberti's 1467 invention. Turning the inner disk changes the alphabet, and turning it during a message makes the first polyalphabetic cipher.</p>
    <div class="panel"><label for="s">Inner disk rotation: <b id="v"></b></label><input id="s" type="range" min="0" max="25" value="3"><label for="m">Message</label><input id="m" value="ATTACK AT DAWN"><label for="p">Rotate the disk by one every N letters (0 = never)</label><input id="p" type="number" min="0" max="20" value="0"></div>
    <div class="panel center"><div id="d"></div><h3>Ciphertext</h3><pre id="o"></pre></div>`;
  const ring = (r, rot, cls) => [...AZ].map((c, i) => { const a = (i * 360 / 26 + rot) * Math.PI / 180; return `<text x="${170 + r * Math.sin(a)}" y="${174 + -r * Math.cos(a)}" class="${cls}">${c}</text>`; }).join("");
  const draw = () => {
    const s = +$("#s").value, p = +$("#p").value, t = clean($("#m").value);
    $("#v").textContent = `${s} (A sits under ${AZ[mod26(-s)]})`;
    $("#d").innerHTML = `<svg viewBox="0 0 340 340" class="disk" role="img" aria-label="Two concentric alphabet rings"><circle cx="170" cy="170" r="162" class="drum"/><circle cx="170" cy="170" r="122" class="inner"/>${ring(140, 0, "outerl")}<g>${ring(102, s * 360 / 26, "innerl")}</g></svg>`;
    $("#o").textContent = [...t].map((c, i) => AZ[mod26(idx(c) - s - (p ? Math.floor(i / p) : 0))]).join("");
  };
  ["s", "p", "m"].forEach(i => { $("#" + i).oninput = draw; }); draw();
}, "machines");

route(/^\/machine\/jefferson$/, async () => {
  const { discs } = await api("/machines/jefferson");
  view().innerHTML = `${backLink}<h1>Jefferson wheel</h1><p class="lead">Each column is one disc. The discs are turned so the message reads along the gold row, and any other row is sent.</p>
    <div class="panel"><label for="m">Message (up to 16 letters)</label><input id="m" value="MEET AT MONTICELLO" maxlength="24"><label for="o">Disc order</label><input id="o" value="3,1,4,1,5,9,2,6"><label for="f">Row sent: <b id="fv"></b> below the message</label><input id="f" type="range" min="1" max="25" value="5"></div>
    <div class="panel scroll"><div id="w"></div><h3>Ciphertext</h3><pre id="c"></pre></div>`;
  const draw = () => {
    const t = clean($("#m").value).slice(0, 16), f = +$("#f").value, order = $("#o").value.split(",").map(Number);
    $("#fv").textContent = f;
    const col = [...t].map((c, i) => { const d = discs[order[i % order.length]] || discs[0], at = d.indexOf(c); return [...Array(26).keys()].map(k => d[(at + k - 6 + 26) % 26]); });
    let html = "";
    for (let r = 0; r < 26; r++) html += `<tr class="${r === 6 ? "mrow" : r === (6 + f) % 26 ? "srow" : ""}">${col.map(c => `<td class="cell">${c[r]}</td>`).join("")}</tr>`;
    $("#w").innerHTML = `<table class="tight"><tbody>${html}</tbody></table>`;
    $("#c").textContent = col.map(c => c[(6 + f) % 26]).join("");
  };
  ["m", "o", "f"].forEach(i => { $("#" + i).oninput = draw; }); draw();
}, "machines");

route(/^\/machine\/grille$/, async () => {
  view().innerHTML = `${backLink}<h1>Turning grille</h1><p class="lead">Write through the holes, rotate the card a quarter turn, and repeat. The four positions together cover every cell exactly once.</p>
    <div class="panel"><label for="m">Message</label><input id="m" value="HOLES IN A ROTATING CARD REVEAL THE WORDS"><label for="k">Key: nine digits from 0 to 3</label><input id="k" value="012301230" maxlength="9"><button id="t">Rotate and write</button><button id="r" class="alt">Start again</button></div>
    <div class="panel center"><div id="g"></div><p id="n" class="mute"></p></div>`;
  let turn = 0;
  const draw = () => {
    const t = clean($("#m").value).padEnd(36, "X"), key = $("#k").value;
    if (!/^[0-3]{9}$/.test(key)) { $("#n").textContent = "The key needs nine digits from 0 to 3."; return; }
    let holes = grilleHoles(key), used = 0;
    const grid = Array(36).fill("");
    for (let q = 0; q < turn; q++) {
      [...holes].map(p => p[0] * 6 + p[1]).sort((a, b) => a - b).forEach(i => { grid[i] = t[used++]; });
      holes = grilleRotate(holes);
    }
    const open = new Set(holes.map(p => p[0] * 6 + p[1]));
    $("#g").innerHTML = `<table class="grille"><tbody>${[...Array(6).keys()].map(r => `<tr>${[...Array(6).keys()].map(c => `<td class="${open.has(r * 6 + c) && turn < 4 ? "hole" : ""}">${grid[r * 6 + c]}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
    $("#n").textContent = turn < 4 ? `Quarter turns written: ${turn}. Lit cells are the holes in the card's current position.` : `Finished. Reading row by row gives: ${grid.join("")}`;
    $("#t").disabled = turn >= 4;
  };
  $("#t").onclick = () => { turn = Math.min(4, turn + 1); draw(); }; $("#r").onclick = () => { turn = 0; draw(); };
  $("#m").oninput = draw; $("#k").oninput = draw; draw();
}, "machines");

route(/^\/machine\/lorenz$/, async () => {
  const { sizes, wheels } = await api("/machines/lorenz");
  view().innerHTML = `${backLink}<h1>Lorenz teleprinter model</h1><p class="lead">A teaching model of the German teleprinter cipher that Colossus attacked. Each character's five bits are combined with two wheels per bit. The second row of wheels moves every other character.</p>
    <div class="panel"><label for="s">Wheel starts, ten numbers</label><input id="s" value="1,2,3,4,5,6,7,8,9,10"><label for="m">Message</label><input id="m" value="GEHEIMSCHREIBER"><button id="n">Next character</button><button id="r" class="alt">Reset</button></div>
    <div class="panel scroll"><div id="w"></div><div id="x"></div><h3>Output so far</h3><pre id="o"> </pre></div>`;
  let i = 0;
  const stream = (j, st) => [0, 1, 2, 3, 4].map(b => [wheels[b][(st[b] + j) % sizes[b]], wheels[b + 5][(st[b + 5] + Math.floor(j / 2)) % sizes[b + 5]]]);
  const draw = () => {
    const st = $("#s").value.split(",").map(Number), t = clean($("#m").value);
    const show = (w, p) => [-7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7].map(d => { const size = w.length, v = w[((p + d) % size + size) % size]; return `<span class="pinbit ${v ? "up" : ""} ${d === 0 ? "now" : ""}"></span>`; }).join("");
    const j = Math.min(i, Math.max(t.length - 1, 0));
    $("#w").innerHTML = [0, 1, 2, 3, 4].map(b => `<div class="wheelrow"><small>Bit ${b}</small><span>${show(wheels[b], st[b] + j)}</span><small>then</small><span>${show(wheels[b + 5], st[b + 5] + Math.floor(j / 2))}</span></div>`).join("");
    const bits = stream(j, st), c = idx(t[j] || "A"), key = bits.reduce((v, [a, b], n) => v | ((a ^ b) << n), 0);
    $("#x").innerHTML = t.length ? table(["Letter", "Letter as bits", "Key bits", "XOR result"], [[t[j], c.toString(2).padStart(5, "0"), key.toString(2).padStart(5, "0"), (c ^ key).toString(2).padStart(5, "0")]]) : "";
    $("#o").textContent = [...t.slice(0, i)].map((ch, n) => String(idx(ch) ^ stream(n, st).reduce((v, [a, b], q) => v | ((a ^ b) << q), 0)).padStart(2, "0")).join(" ") || " ";
    $("#n").disabled = i >= t.length;
  };
  $("#n").onclick = () => { i++; draw(); }; $("#r").onclick = () => { i = 0; draw(); };
  $("#s").oninput = draw; $("#m").oninput = () => { i = 0; draw(); }; draw();
}, "machines");
