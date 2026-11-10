/* Logic Analyser: which protocol is on these wires, and what does it carry? */
function lgWave(w, marks) {
  const names = Object.keys(w.channels), W = 1000, row = 46, H = names.length * row + 30, T = w.duration || 1;
  const x = t => 70 + t / T * (W - 80);
  const lines = names.map((n, i) => {
    const y0 = 20 + i * row, hi = y0 + 6, lo = y0 + 30, pts = [];
    const st = w.channels[n];
    st.forEach(([t, v], j) => { const nx = j + 1 < st.length ? st[j + 1][0] : T; if (j) pts.push(`${x(t)},${v ? lo : hi}`); pts.push(`${x(t)},${v ? hi : lo}`, `${x(nx)},${v ? hi : lo}`); });
    return `<text x="4" y="${y0 + 22}" fill="var(--ink)" font-size="12">${esc(n)}</text><polyline fill="none" stroke="var(--c1)" stroke-width="1.5" points="${pts.join(" ")}"/>`;
  }).join("");
  const ms = (marks || []).slice(0, 120).map(([t, v, ok]) => `<text x="${x(t)}" y="${H - 6}" fill="${ok ? "var(--ink)" : "var(--bad)"}" font-size="10">${v >= 32 && v < 127 ? esc(String.fromCharCode(v)) : v.toString(16).padStart(2, "0")}</text>`).join("");
  return `<div style="overflow-x:auto"><svg viewBox="0 0 ${W} ${H}" style="width:100%;min-width:700px;background:#05040e" role="img" aria-label="Logic waveforms with decoded bytes">${lines}${ms}</svg></div>`;
}

const LG_REQ = { 0: "GET_STATUS", 1: "CLEAR_FEATURE", 3: "SET_FEATURE", 5: "SET_ADDRESS", 6: "GET_DESCRIPTOR", 7: "SET_DESCRIPTOR", 8: "GET_CONFIGURATION", 9: "SET_CONFIGURATION" };
const LG_DESC = { 1: "device", 2: "configuration", 3: "string", 4: "interface", 5: "endpoint" };
function lgSetup(d) {
  /* Name a standard 8-byte SETUP request, the first thing a host asks any new device. */
  if (d.length !== 8 || (d[0] & 0x60) !== 0 || !(d[1] in LG_REQ)) return "";
  const name = LG_REQ[d[1]], extra = d[1] === 6 ? ` ${LG_DESC[d[3]] || `type ${d[3]}`} descriptor, ${d[6] | (d[7] << 8)} bytes` : d[1] === 5 ? ` to ${d[2]}` : "";
  return `${name}${extra}`;
}

function lgShow(r) {
  const best = r.ranking[0], rel = r.reliability;
  const detail = !best ? "" : best.protocol === "USB" ? table(["Packet", "Address", "Endpoint", "Bytes", "Check"], best.packets.map(p => [p.pid || p.error, p.addr ?? "", p.endp ?? "", p.data ? lgSetup(p.data) || p.data.map(v => v.toString(16).padStart(2, "0")).join(" ") : "", p.error ? p.error : p.ok ? "CRC correct" : "CRC wrong"]))
    : best.protocol.endsWith("infrared") ? table(["Address", "Command", "Check"], best.frames.map(f => [f.address, f.command, f.ok ? "passes" : "fails"]))
    : best.protocol === "CAN" ? table(["ID", "Data", "CRC"], best.frames.map(f => [`0x${f.id.toString(16)}`, f.data.map(v => v.toString(16).padStart(2, "0")).join(" "), f.crc_ok ? "correct" : "wrong"]))
    : best.protocol === "I2C" ? table(["Address", "Direction", "Bytes", "All acknowledged"], best.messages.map(m => [`0x${m.address.toString(16)}`, m.read ? "read" : "write", m.data.length, m.acks.every(Boolean) ? "yes" : "no"])) : "";
  const settings = b => [b.baud && `${b.baud} baud`, b.bitrate && `${b.bitrate / 1000} kbit/s`, b.mode !== undefined && `mode ${b.mode}`, b.inverted && "inverted", b.resets !== undefined && `${b.resets} reset(s)`, b.speed && `${b.speed} speed`, b.messages && b.messages.length && `address 0x${b.messages[0].address.toString(16)}`].filter(Boolean).join(", ");
  $("#lgOut").innerHTML = `<div class="panel cverdict ${best ? "readable" : "none"}"><h3>${best ? `${esc(best.protocol)}${settings(best) ? `: ${esc(settings(best))}` : ""}` : "No protocol recognised"}</h3>
      ${best ? `<p class="reading">${esc(best.text)}</p><p class="mute">${esc(best.hex)}</p>` : ""}${r.truth && r.truth.protocol ? `<p class="mute">Generated as ${esc(r.truth.protocol)}, ${esc(r.truth.settings)}.</p>` : ""}</div>
    <div class="panel"><h3>The wires</h3>${lgWave(r.wave, best && best.marks)}<p class="mute">Decoded values are written along the bottom; red ones failed a check.</p></div>
    <div class="panel"><h3>Every protocol tried</h3>${table(["Protocol", "Wiring", "Score", "Errors", "Decoded"], r.ranking.map(x => [x.protocol, Object.entries(x.wiring).map(([k, v]) => `${k}=${v}`).join(" "), x.score, x.errors ?? "", x.text.slice(0, 40)]))}
      <p class="mute">Each decoder is run on every plausible wiring. Scores count only units that pass the protocol's own checks, weighted by how hard those checks are to pass by chance: a CAN CRC-15 almost never, two UART framing bits often. In ${rel.trials} generated captures with glitches, the protocol and every byte were found ${rel.bytes_ok} times.</p>${detail}</div>`;
}

route(/^\/logic$/, async () => {
  view().innerHTML = `<p class="kicker">// LOGIC ANALYSER</p><h1>Logic Analyser</h1><p class="lead">A logic analyser records the voltage on each wire as 0s and 1s. To read it you must know the protocol, its speed and which wire does what. This page works all three out.</p>
    <div class="panel"><div class="row"><div><label for="lgK">Generate a capture</label><select id="lgK"><option value="uart">UART serial</option><option value="spi">SPI</option><option value="i2c">I2C</option><option value="can">CAN bus</option><option value="onewire">1-Wire</option><option value="usb">USB (full speed)</option><option value="nec">NEC infrared remote</option><option value="rc5">RC5 infrared remote</option></select></div>
    <div><label for="lgM">Message</label><input id="lgM" value="Code Breaker"></div><div><label for="lgG">Glitches</label><input id="lgG" type="number" min="0" max="20" value="3"></div></div><button id="lgGo">Generate and decode</button>
    <label class="filebtn">Or open a logic-analyser CSV<input id="lgF" type="file" accept=".csv,.txt"></label> <span class="mute">A time column (seconds) and one 0/1 column per wire, as exported by sigrok or Saleae.</span><p id="lgMsg" aria-live="polite"></p></div><div id="lgOut"></div>`;
  $("#lgGo").onclick = ev => busy(ev.target, $("#lgMsg"), async () => lgShow(await api("/signals/logic", { example: $("#lgK").value, message: $("#lgM").value, glitches: +$("#lgG").value })));
  $("#lgF").onchange = ev => busy(ev.target.parentElement, $("#lgMsg"), async () => { const f = ev.target.files[0]; if (f) lgShow(await api("/signals/logic", { csv: await f.text() })); });
}, "logic");
