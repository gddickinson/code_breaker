/* Registers of open codes, and of verified and candidate solutions. */
route(/^\/open$/, async () => {
  const d = await api("/codes/open");
  const cats = ["All", ...new Set(d.codes.map(c => c.category || "other"))];
  let cat = "All", dataOnly = false;
  view().innerHTML = `<p class="kicker">// OPEN_FILES</p><h1>Open codes</h1><p class="lead">Every unsolved code and undeciphered script we track. Some have ciphertext we can attack, and others are waiting for a verified transcription.</p>
    <div class="tiles"><div class="tile"><b>${d.codes.length}</b><span>Open entries</span></div><div class="tile"><b>${d.codes.filter(c => c.data_path).length}</b><span>With verified data</span></div><div class="tile"><b>${d.codes.filter(c => c.leads).length}</b><span>With live leads</span></div><div class="tile"><b>${d.extra[0].count.toLocaleString()}</b><span>Further Le Figaro ads</span></div></div>
    <div class="verdict"><a href="${esc(d.extra[0].href)}">${esc(d.extra[0].name)}</a>: ${esc(d.extra[0].note)}</div>
    <div class="row filters"><div><label for="q">Search</label><input id="q" placeholder="Name or status"></div><div><label for="c">Type</label><select id="c">${cats.map(c => `<option>${esc(c)}</option>`).join("")}</select></div><div><label for="d"><input id="d" type="checkbox" class="check"> Only with data we can attack</label></div></div><p id="n" class="mute"></p><div id="t"></div>`;
  const draw = () => {
    const q = $("#q").value.toLowerCase();
    const rows = d.codes.filter(c => (cat === "All" || (c.category || "other") === cat) && (!dataOnly || c.data_path) && `${c.name} ${c.status} ${c.origin}`.toLowerCase().includes(q));
    $("#n").textContent = `${rows.length} shown`;
    $("#t").innerHTML = `<div class="scroll"><table><thead><tr>${["Code", "Type", "Status", "Origin", "Length", "Symbols", "Leads", "Attempts"].map(x => `<th scope="col">${x}</th>`).join("")}</tr></thead><tbody>${rows.map(c => `<tr><td><a href="#/lead/${esc(c.slug)}">${esc(c.name)}</a></td><td>${esc(c.category)}</td><td>${esc(c.status)}</td><td>${esc(c.origin)}</td><td>${c.tokens ?? "no data yet"}</td><td>${c.symbols ?? ""}</td><td>${c.leads}</td><td>${c.attempts}</td></tr>`).join("")}</tbody></table></div>`;
  };
  $("#q").oninput = draw; $("#c").onchange = e => { cat = e.target.value; draw(); }; $("#d").onchange = e => { dataOnly = e.target.checked; draw(); }; draw();
}, "open");

const TIERS = { passes: ["Passes all checks", "good", "Passes the control, the shuffled comparison and the word check, and has been read against its scan."], strong: ["Strong candidate", "warn", "Reads convincingly or is supported independently, but has not passed every automatic check."], partial: ["Partial reading", "bad", "Parts of the message are visible. Other parts are uncertain or missing."] };

route(/^\/solutions$/, async () => {
  const d = await api("/solutions");
  const group = k => d.candidates.filter(c => c.tier === k);
  const card = c => `<div class="panel"><span class="tag ${TIERS[c.tier][1]}">${TIERS[c.tier][0]}</span> <a href="#/lead/${esc(c.code)}">${esc(c.name)}</a><h3>${esc(c.title)}</h3><p class="reading">${esc(c.detail.split("\n")[0])}</p><p class="mute">${esc(c.evidence)}</p></div>`;
  view().innerHTML = `<p class="kicker">// SOLUTIONS_REGISTER</p><h1>Solutions and possible solutions</h1><p class="lead">What these tools have actually read, sorted by how far each result can be trusted.</p>
    <div class="verdict">No famous unsolved cipher has been cracked here. Possible solutions may already be known to others: being listed as undecrypted does not prove nobody has read a message.</div>
    <h2>Possible solutions</h2>${Object.entries(TIERS).map(([k, t]) => `<h3>${t[0]} (${group(k).length})</h3><p class="mute">${t[2]}</p>${group(k).map(card).join("") || '<p class="mute">None yet.</p>'}`).join("")}
    <h2>Known solutions our tools reproduced</h2><p class="mute">These were solved by others first. They prove the tools work.</p>
    ${table(["Cipher", "Opening of the text", "Method", "First solved"], d.verified.map(v => [v.name, v.text, v.how, v.solved_by]))}
    <div class="row">${d.verified.map(v => `<a class="cta" href="${esc(v.href)}">${esc(v.name.split(" (")[0])}</a>`).join("")}</div>`;
}, "solutions");
