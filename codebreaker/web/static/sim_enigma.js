/* Interactive Enigma I: type on the keyboard, watch rotors step and current flow. */
const LAYOUT = ["QWERTZUIO", "ASDFGHJK", "PYXCVBNML"];
const Y = i => 34 + i * 15;
const COL = { reflector: 58, rotors: [[150, 268], [342, 460], [534, 652]], entry: 742 };

function enigmaSvg(m, press) {
  const contact = (x, labelFn) => AZ.split("").map((_, i) => `<circle cx="${x}" cy="${Y(i)}" r="2.5" class="pin"/>${labelFn ? `<text x="${x}" y="${Y(i) + 3}" class="pinlabel">${labelFn(i)}</text>` : ""}`).join("");
  let body = "";
  m.names.forEach((name, r) => {
    const [l, rx] = COL.rotors[r];
    const o = m.offset(r);
    const wires = [...Array(26).keys()].map(i => {
      const out = mod26(m.wires[r][mod26(i + o)] - o);
      return `<line x1="${rx}" y1="${Y(i)}" x2="${l}" y2="${Y(out)}" class="wire"/>`;
    }).join("");
    const moved = press && press.moved[r];
    body += `<g class="${moved ? "rotormoved" : ""}"><rect x="${l - 18}" y="18" width="${rx - l + 36}" height="${Y(25) - 18 + 16}" rx="8" class="drum"/>${wires}
      ${contact(l)}${contact(rx, i => AZ[(i + m.pos[r]) % 26])}
      <text x="${(l + rx) / 2}" y="13" class="rname">Rotor ${name}</text></g>`;
    if (r < 2) body += [...Array(26).keys()].map(i => `<line x1="${rx}" y1="${Y(i)}" x2="${COL.rotors[r + 1][0]}" y2="${Y(i)}" class="link"/>`).join("");
  });
  const seen = new Set();
  const arcs = m.reflector.map((j, i) => {
    if (seen.has(i) || seen.has(j)) return "";
    seen.add(i); seen.add(j);
    return `<path d="M ${COL.reflector + 40} ${Y(i)} C ${COL.reflector - 10 - Math.abs(i - j) * 2} ${Y(i)}, ${COL.reflector - 10 - Math.abs(i - j) * 2} ${Y(j)}, ${COL.reflector + 40} ${Y(j)}" class="wire"/>`;
  }).join("");
  const link0 = [...Array(26).keys()].map(i => `<line x1="${COL.reflector + 40}" y1="${Y(i)}" x2="${COL.rotors[0][0]}" y2="${Y(i)}" class="link"/>`).join("");
  const linkE = [...Array(26).keys()].map(i => `<line x1="${COL.rotors[2][1]}" y1="${Y(i)}" x2="${COL.entry}" y2="${Y(i)}" class="link"/>`).join("");
  let paths = "";
  if (press) {
    const f = [`${COL.entry} ${Y(press.entry)}`];
    press.forward.forEach(s => { const [l, rx] = COL.rotors[s.rotor]; f.push(`${rx} ${Y(s.from)}`, `${l} ${Y(s.to)}`); });
    f.push(`${COL.reflector + 40} ${Y(press.reflect[0])}`);
    const [a, b] = press.reflect, bend = COL.reflector - 10 - Math.abs(a - b) * 2;
    const back = [`${COL.reflector + 40} ${Y(b)}`];
    press.back.forEach(s => { const [l, rx] = COL.rotors[s.rotor]; back.push(`${l} ${Y(s.from)}`, `${rx} ${Y(s.to)}`); });
    back.push(`${COL.entry} ${Y(press.exit)}`);
    paths = `<path pathLength="1" class="flow out" d="M ${f.join(" L ")} C ${bend} ${Y(a)}, ${bend} ${Y(b)}, ${COL.reflector + 40} ${Y(b)} L ${back.slice(1).join(" L ")}"/>`;
  }
  return `<svg viewBox="0 0 790 442" class="enigma" role="img" aria-label="Wiring of the rotors, with the current path highlighted">
    <rect x="${COL.reflector - 50}" y="18" width="98" height="${Y(25) - 2}" rx="8" class="drum"/><text x="${COL.reflector}" y="13" class="rname">Reflector B</text>
    ${arcs}${link0}${contact(COL.reflector + 40)}${body}${linkE}${contact(COL.entry, i => AZ[i])}<text x="${COL.entry}" y="13" class="rname">Entry</text>${paths}</svg>`;
}

route(/^\/machine\/enigma$/, async () => {
  view().innerHTML = `<a href="#/machines">← Machines</a><h1>Enigma I</h1>
    <p class="lead">Press a key. The rotors step first, then the current runs through the plugboard, three rotors and the reflector, and comes back by a different route to light a lamp.</p>
    <div class="panel"><div class="row">
      ${[0, 1, 2].map(i => `<div><label for="r${i}">${["Left", "Middle", "Right"][i]} rotor</label><select id="r${i}">${Object.keys(ROTOR_DATA).map(n => `<option ${n === ["I", "II", "III"][i] ? "selected" : ""}>${n}</option>`).join("")}</select></div>`).join("")}
      <div><label for="ring">Rings</label><input id="ring" value="AAA" maxlength="3"></div><div><label for="start">Start</label><input id="start" value="ADU" maxlength="3"></div>
      <div><label for="plug">Plugboard</label><input id="plug" value="AV BS CG"></div></div>
      <button id="apply">Apply settings</button><button id="demo" class="alt">Show the double step</button><span id="setErr" class="err"></span></div>
    <div class="windows" id="windows" aria-live="polite"></div><div id="wiring" class="scroll"></div>
    <div class="lamps" id="lamps"></div><div class="keys" id="keys"></div>
    <div class="two"><div class="panel"><h3>Typed</h3><pre id="tin"> </pre><h3>Lit lamps (ciphertext)</h3><pre id="tout"> </pre><button id="back" class="alt">Decrypt this: reset and retype</button></div>
    <div class="panel"><h3>Last keypress</h3><div id="trace" class="mute">Press a key, or use your computer keyboard.</div></div></div>`;
  let m, typed = "", lit = "", timer;
  const layout = (id, cls) => { $(id).innerHTML = LAYOUT.map(r => `<div>${[...r].map(c => `<${cls === "key" ? 'button type="button"' : "span"} class="${cls}" data-c="${c}">${c}</${cls === "key" ? "button" : "span"}>`).join("")}</div>`).join(""); };
  layout("#lamps", "lamp");
  layout("#keys", "key");
  const windows = press => { $("#windows").innerHTML = m.pos.map((p, r) => `<div class="window ${press && press.moved[r] ? "tick" : ""}"><small>${["Left", "Middle", "Right"][r]}${p === m.notch[r] ? " · at notch" : ""}</small><b>${AZ[p]}</b></div>`).join(""); };
  const draw = press => { $("#wiring").innerHTML = enigmaSvg(m, press); windows(press); };
  const setup = () => {
    try {
      m = new Enigma({ rotors: [0, 1, 2].map(i => $("#r" + i).value), ring: $("#ring").value, start: $("#start").value, plugboard: $("#plug").value });
      if (new Set(m.names).size !== 3) throw new Error("Each rotor can be used only once.");
      if (m.ring.length !== 3 || m.pos.length !== 3 || m.ring.concat(m.pos).some(v => v < 0)) throw new Error("Rings and start need three letters.");
      $("#setErr").textContent = ""; typed = lit = ""; $("#tin").textContent = " "; $("#tout").textContent = " "; draw(null);
    } catch (e) { $("#setErr").textContent = e.message; }
  };
  const press = letter => {
    if (!m) return;
    const r = m.press(letter);
    typed += letter; lit += r.letter;
    $("#tin").textContent = typed; $("#tout").textContent = lit;
    draw(r);
    document.querySelectorAll(".lamp").forEach(l => l.classList.toggle("on", l.dataset.c === r.letter));
    clearTimeout(timer);
    timer = setTimeout(() => document.querySelectorAll(".lamp.on").forEach(l => l.classList.remove("on")), 1400);
    $("#trace").innerHTML = `<p>${esc(r.note)}</p>${table(["Stage", "In", "Out"], r.stages.map(s => [s.part, AZ[s.from], AZ[s.to]]))}<p class="mute">A letter can never light its own lamp, because the reflector always sends the current back on a different wire. Bletchley Park exploited exactly that.</p>`;
  };
  document.querySelectorAll(".key").forEach(k => { k.onclick = () => press(k.dataset.c); });
  $("#apply").onclick = setup;
  $("#demo").onclick = () => { $("#r0").value = "I"; $("#r1").value = "II"; $("#r2").value = "III"; $("#ring").value = "AAA"; $("#start").value = "ADU"; setup(); $("#trace").textContent = "Middle rotor II has its notch at E, and right rotor III turns over at V. Press any key three times: the middle rotor moves on two consecutive presses."; };
  $("#back").onclick = () => { const ct = lit; setup(); [...ct].forEach(press); };
  const onKey = e => {
    if (!location.hash.startsWith("#/machine/enigma")) { window.removeEventListener("keydown", onKey); return; }
    if (e.metaKey || e.ctrlKey || e.altKey || /INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) return;
    const c = e.key.toUpperCase();
    if (c.length === 1 && AZ.includes(c)) { e.preventDefault(); press(c); }
  };
  window.addEventListener("keydown", onKey);
  setup();
}, "machines");
