/* Line Codes: how bytes become the 0s and 1s on a wire, and how to tell which code a bitstream uses. */
const LC_INFO = [
  ["Manchester", "Each bit is a transition in the middle of its slot: low-to-high for 1, high-to-low for 0 (IEEE 802.3). The clock can never be lost, at the cost of doubling the signalling rate. Used by 10BASE-T Ethernet and many RFID tags."],
  ["4B5B", "Each 4-bit nibble becomes a 5-bit symbol with no long runs of zeros, then NRZI sends a 1 as a change of level. Spare symbols mark idle, start (J K) and end (T R). Used by FDDI and 100 Mbit Ethernet."],
  ["8b/10b", "Each byte becomes 10 bits chosen so that ones and zeros stay balanced, tracked by a running disparity. The comma K28.5 contains a pattern that cannot occur elsewhere, so a receiver can find symbol boundaries. Used by gigabit Ethernet, SATA, PCI Express 1 and 2, USB 3 and DisplayPort."],
  ["TMDS", "HDMI and DVI send each colour channel as 10-bit symbols that first minimise transitions and then invert when needed for balance. Four control tokens fill the blanking intervals, which is how a receiver locks on."],
];
const LC_SIZE = { "Manchester": 2, "4B5B": 5, "8b/10b": 10, "TMDS": 10 };

function lcShow(r) {
  const best = r.ranking[0], st = r.stats, rel = r.reliability, d = best.detail || {};
  const size = LC_SIZE[best.code] || 8, off = d.offset || 0, bits = r.preview;
  const grouped = best.score ? `${esc(bits.slice(0, off))} ${(bits.slice(off).match(new RegExp(`.{1,${size}}`, "g")) || []).slice(0, 24).map(g => `<span style="margin-right:6px">${esc(g)}</span>`).join("")}` : esc(bits.slice(0, 200));
  const eth = best.code === "Manchester" && d.dst ? table(["Destination", "Source", "EtherType", "Frame check (CRC-32)"], [[d.dst, d.src, d.ethertype, d.crc_ok ? "correct" : "wrong"]]) : "";
  $("#lcOut").innerHTML = `<div class="panel cverdict ${best.score ? "readable" : "none"}"><h3>${best.score ? esc(best.code) : "No line code recognised"}</h3>${best.score ? `<p class="reading">${esc(best.text)}</p>` : ""}${r.truth && r.truth.code ? `<p class="mute">Generated as ${esc(r.truth.code)}: ${esc(r.truth.carrier)}.</p>` : ""}${eth}</div>
    <div class="panel"><h3>The bits, split into symbols</h3><p class="reading" style="word-break:break-all;font-size:13px">${grouped}</p><p class="mute">${best.score ? `Split every ${size} bits from offset ${off}, found ${best.code === "8b/10b" ? "from the comma" : best.code === "TMDS" ? "from repeated control tokens" : best.code === "4B5B" ? "from the J K start delimiter" : "from the transition in every bit"}.` : ""}</p>
      ${table(["Bits", "Longest run", "Share of 1s", "Worst imbalance"], [[st.bits, st.longest_run, st.ones_share, st.worst_imbalance]])}<p class="mute">Short runs keep the receiver's clock locked; a balanced share of 1s lets the signal pass through transformers and capacitors.</p></div>
    <div class="panel"><h3>Every code tried</h3>${table(["Code", "Valid symbols", "Score", "Decoded"], r.ranking.map(x => [x.code, `${Math.round(x.valid * 100)}%`, x.score, x.text.slice(0, 40)]))}<p class="mute">In ${rel.trials} generated streams, the code and the full message were found ${rel.bytes_ok} times. A flipped bit usually still leaves the code recognisable, but these codes detect errors rather than correct them.</p></div>`;
}

route(/^\/linecodes$/, async () => {
  view().innerHTML = `<p class="kicker">// LINE CODES</p><h1>Line codes</h1><p class="lead">Between bytes and voltages sits a line code. It keeps the receiver's clock locked, keeps the signal balanced, and marks where symbols begin. Recognising it is the first step in reading any wire or fibre.</p>
    <div class="panel"><div class="row"><div><label for="lcK">Generate a bitstream</label><select id="lcK"><option value="manchester">Manchester (10BASE-T Ethernet)</option><option value="4b5b">4B5B with NRZI (FDDI, 100 Mbit)</option><option value="8b10b" selected>8b/10b (gigabit Ethernet, SATA, PCIe)</option><option value="tmds">TMDS (HDMI, DVI)</option></select></div>
    <div><label for="lcM">Message</label><input id="lcM" value="Hello, wire"></div><div><label for="lcE">Bit errors</label><input id="lcE" type="number" min="0" max="20" value="0"></div></div><button id="lcGo">Generate and identify</button>
    <label for="lcB">Or paste bits (0s and 1s)</label><textarea id="lcB" rows="3" placeholder="0011111010..."></textarea><button id="lcP" class="alt">Identify pasted bits</button><p id="lcMsg" aria-live="polite"></p></div><div id="lcOut"></div>
    <h2>The four codes</h2><div class="biogrid">${LC_INFO.map(([t, b]) => `<div class="panel"><h3>${esc(t)}</h3><p>${esc(b)}</p></div>`).join("")}</div>
    <p class="mute">Related: <a href="#/logic">Logic Analyser</a> for UART, SPI, I2C, CAN, 1-Wire and USB; <a href="#/theory/detection">error detection</a> for CRCs.</p>`;
  $("#lcGo").onclick = ev => busy(ev.target, $("#lcMsg"), async () => lcShow(await api("/signals/linecode", { example: $("#lcK").value, message: $("#lcM").value, errors: +$("#lcE").value })));
  $("#lcP").onclick = ev => busy(ev.target, $("#lcMsg"), async () => lcShow(await api("/signals/linecode", { bits: $("#lcB").value })));
}, "linecodes");
