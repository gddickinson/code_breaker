/* Codes in nature: biological information, deception, and two small interactive models. */
const BIO_CHANNELS = [["Chemical", "Slow", "Metres to kilometres downwind", "Lasts after the sender leaves; works in the dark", "Hard to switch off quickly"], ["Light and colour", "Instant", "Line of sight", "Fast and detailed", "Blocked by obstacles; visible to predators"], ["Sound", "Fast", "Long, especially in water", "Travels around obstacles and in the dark", "Easy for eavesdroppers to locate"], ["Vibration", "Fast", "Along the same plant or ground", "Private from airborne listeners", "Limited to a connected surface"], ["Electric", "Instant", "Centimetres to metres in water", "Works in murky water", "Short range"], ["Touch and dance", "Fast", "Contact", "Rich, as in the bee dance", "Only to those present"]];
const BASES = "TCAG", AMINO = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG";
function translateDNA(seq) {
  const s = seq.toUpperCase().replace(/U/g, "T").replace(/[^ACGT]/g, ""), out = [];
  for (let i = 0; i + 3 <= s.length; i += 3) out.push(AMINO[BASES.indexOf(s[i]) * 16 + BASES.indexOf(s[i + 1]) * 4 + BASES.indexOf(s[i + 2])]);
  return out.join("");
}

route(/^\/biology$/, async () => {
  const d = await (await fetch("/static/biology.json")).json(), groups = [...new Set(d.map(x => x.group))];
  const NAMES = { F: "Phe", L: "Leu", I: "Ile", M: "Met", V: "Val", S: "Ser", P: "Pro", T: "Thr", A: "Ala", Y: "Tyr", "*": "Stop", H: "His", Q: "Gln", N: "Asn", K: "Lys", D: "Asp", E: "Glu", C: "Cys", W: "Trp", R: "Arg", G: "Gly" };
  const table = () => `<div class="scroll"><table class="tight codon"><thead><tr><th></th>${[...BASES].map(b => `<th scope="col">${b}</th>`).join("")}</tr></thead><tbody>${[...BASES].map((a, i) => [...BASES].map((c, k) => `<tr><th scope="row">${a}·${c}</th>${[...BASES].map((b, j) => { const v = AMINO[i * 16 + j * 4 + k]; return `<td class="aa aa-${v === "*" ? "stop" : v}" data-c="${a}${b}${c}" title="${a}${b}${c}">${NAMES[v]}</td>`; }).join("")}</tr>`).join("")).join("")}</tbody></table></div>`;
  view().innerHTML = `<p class="kicker">// LIVING_SYSTEMS</p><h1>Codes in nature</h1><p class="lead">Life stores, copies, encrypts and forges information. Many ideas that codebreakers rediscovered were already at work in cells and animals.</p><div class="panel"><h3>Choosing a channel</h3>${window.table(["Channel", "Speed", "Range", "Strengths", "Weaknesses"], BIO_CHANNELS)}<p class="mute">Each channel trades speed, range and privacy differently, so animals often use several. Recordings of birdsong can be analysed in the <a href="#/sounds">Sound Lab</a>.</p></div>
    ${groups.map(g => `<h2>${esc(g)}</h2><div class="biogrid">${d.filter(x => x.group === g).map(x => `<div class="panel"><h3>${esc(x.title)}</h3><p>${esc(x.text)}</p>${x.encoding ? `<p class="mute"><b>How it is encoded:</b> ${esc(x.encoding)}</p>` : ""}</div>`).join("")}</div>${g === "The genetic code" ? `<div class="panel"><h3>Translate DNA into protein</h3><label for="dna">DNA or RNA sequence</label><textarea id="dna">ATGGCCATTGTAATGGGCCGCTGAAAGGGTGCCCGATAG</textarea><pre id="pro"></pre><p class="mute">Each row of the table is a first and third base, and each column a second base. Shading links codons for the same amino acid, the homophones of the genetic code.</p>${table()}</div>` : ""}${g === "Signals between animals" ? `<div class="panel"><h3>Read a waggle dance</h3><div class="row"><div><label for="ang">Direction from the sun: <b id="av"></b></label><input id="ang" type="range" min="-180" max="180" value="40"></div><div><label for="dur">Waggle length: <b id="dv"></b></label><input id="dur" type="range" min="2" max="40" value="14"></div></div><div class="center"><svg id="bee" viewBox="0 0 340 340" class="disk" role="img" aria-label="Waggle dance path on a vertical comb"></svg></div><p id="dt" class="mute"></p></div>` : ""}`).join("")}
    <p class="mute">The distance calibration in the dance model is a rough guide, since it varies between colonies and landscapes.</p>`;
  const tr = () => { $("#pro").textContent = translateDNA($("#dna").value) || " "; };
  $("#dna").oninput = tr; tr();
  const bee = () => {
    const a = +$("#ang").value, t = +$("#dur").value / 10, r = a * Math.PI / 180, len = 30 + t * 30, cx = 170, cy = 180;
    const [dx, dy] = [Math.sin(r), -Math.cos(r)], [nx, ny] = [-dy, dx], sx = cx - dx * len / 2, sy = cy - dy * len / 2;
    let wig = `M ${sx} ${sy}`;
    for (let i = 1; i <= 24; i++) { const p = i / 24; wig += ` L ${sx + dx * len * p + nx * (i % 2 ? 9 : -9)} ${sy + dy * len * p + ny * (i % 2 ? 9 : -9)}`; }
    $("#av").textContent = `${a}°`; $("#dv").textContent = `${t.toFixed(1)} s`;
    $("#bee").innerHTML = `<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="var(--c3)"/></marker></defs><line x1="170" y1="46" x2="170" y2="16" stroke="var(--c3)" stroke-width="2" marker-end="url(#ar)"/><text x="182" y="28" class="axisl">up = the sun's direction</text><circle cx="170" cy="180" r="130" fill="none" stroke="var(--line)"/><path d="${wig}" fill="none" stroke="var(--c1)" stroke-width="3"/><path d="M ${sx + dx * len} ${sy + dy * len} C ${sx + dx * len + nx * 80} ${sy + dy * len + ny * 80}, ${sx + nx * 80} ${sy + ny * 80}, ${sx} ${sy}" fill="none" stroke="var(--c4)" stroke-dasharray="4 5"/><path d="M ${sx + dx * len} ${sy + dy * len} C ${sx + dx * len - nx * 80} ${sy + dy * len - ny * 80}, ${sx - nx * 80} ${sy - ny * 80}, ${sx} ${sy}" fill="none" stroke="var(--c4)" stroke-dasharray="4 5"/>`;
    $("#dt").textContent = `Food lies ${Math.abs(a)}° ${a < 0 ? "left" : "right"} of the sun, about ${t.toFixed(1)} km away using a rough guide of one kilometre per second of waggle.`;
  };
  $("#ang").oninput = bee; $("#dur").oninput = bee; bee();
}, "biology");


