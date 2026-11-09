/* Lead Board: every known code, its leads, avenues and the hunter's log. */
const LEAD_STATES = ["open", "needs_review", "testing", "promising", "rejected", "confirmed"];
const stateTag = s => `<span class="tag ${s === "promising" || s === "confirmed" ? "good" : s === "rejected" ? "bad" : "warn"}">${esc(s.replace("_", " "))}</span>`;

route(/^\/leads$/, async () => {
  const d = await api("/leads"), s = d.summary;
  const tiles = [["Codes tracked", s.codes], ["With ciphertext", s.with_data], ["Open leads", s.open_leads], ["Avenues", s.avenues], ["Attempts run", s.attempts], ["Readable hits", s.readable]];
  view().innerHTML = `<p class="kicker">// LEAD_DATABASE</p><h1>Lead Board</h1><p class="lead">Every known mystery, what we know about it, and what is still worth trying. The hunter keeps working through these and writes back here.</p>
    <div class="tiles">${tiles.map(([k, v]) => `<div class="tile"><b>${Number(v).toLocaleString()}</b><span>${k}</span></div>`).join("")}</div>
    <h2>The field</h2>${codeMap(d.codes)}
    <h2>Live leads</h2>${d.leads.map(l => `<div class="panel">${stateTag(l.status)} <a href="#/lead/${esc(l.code)}">${esc(l.code_name)}</a><h3>${esc(l.title)}</h3><p>${esc(l.detail)}</p><p class="mute">${esc(l.evidence)}</p></div>`).join("")}
    <h2>All codes</h2><label for="q">Filter</label><input id="q" class="filter" placeholder="Name or status"><div id="tb"></div>
    <h2>Hunter log</h2>${table(["When (UTC)", "Entry"], d.journal.map(j => [j.at, j.entry]))}`;
  const draw = () => {
    const q = $("#q").value.toLowerCase(), rows = d.codes.filter(c => `${c.name} ${c.status} ${c.category}`.toLowerCase().includes(q));
    $("#tb").innerHTML = `<div class="scroll"><table><thead><tr>${["Code", "Type", "Status", "Length", "Symbols", "Leads", "Attempts"].map(c => `<th scope="col">${c}</th>`).join("")}</tr></thead><tbody>${rows.map(c => `<tr><td><a href="#/lead/${esc(c.slug)}">${esc(c.name)}</a></td><td>${esc(c.category)}</td><td>${esc(c.status)}</td><td>${c.tokens ?? "no data yet"}</td><td>${c.symbols ?? ""}</td><td>${c.open_leads}</td><td>${c.attempts}</td></tr>`).join("")}</tbody></table></div>`;
  };
  $("#q").oninput = draw; draw();
}, "leads");

route(/^\/lead\/([\w-]+)$/, async slug => {
  const d = await api("/leads/" + slug), c = d.code;
  view().innerHTML = `<a href="#/leads">← Lead Board</a><h1>${esc(c.name)}</h1><p><span class="tag">${esc(c.category)}</span><span class="tag warn">${esc(c.status)}</span>${c.origin ? `<span class="tag">${esc(c.origin)}</span>` : ""}</p>
    ${c.data_path ? "" : '<div class="verdict">No verified ciphertext yet, so this entry is on the research list.</div>'}
    <h2>Known facts</h2>${d.facts.length ? `<ul>${d.facts.map(f => `<li>${esc(f.fact)} <span class="mute">(${esc(f.source)})</span></li>`).join("")}</ul>` : '<p class="mute">Nothing recorded yet.</p>'}
    <h2>Leads</h2>${d.leads.map(l => `<div class="panel">${stateTag(l.status)}<h3>${esc(l.title)}</h3><p style="white-space:pre-line">${esc(l.detail)}</p><p class="mute">${esc(l.evidence)}</p><div class="row"><div><label for="s${l.id}">Status</label><select id="s${l.id}">${LEAD_STATES.map(s => `<option ${s === l.status ? "selected" : ""}>${s}</option>`).join("")}</select></div><div><label for="n${l.id}">Note</label><input id="n${l.id}"></div></div><button data-id="${l.id}">Update</button></div>`).join("") || '<p class="mute">No leads yet.</p>'}
    <h2>Avenues</h2>${table(["Method", "Setting", "Language", "Runs", "Best z", "Effort level"], d.avenues.map(a => [a.strategy, a.param, a.lang, a.runs, a.best_z ?? "", a.level]))}
    <h2>Top attempts</h2>${table(["Method", "Language", "z", "Verdict", "Output"], d.attempts.map(t => [`${t.strategy} ${t.param}`, t.lang, t.z, t.verdict.slice(0, 80), t.reading.slice(0, 80)]))}`;
  document.querySelectorAll("button[data-id]").forEach(b => { b.onclick = async () => { await api("/leads/item/" + b.dataset.id, { status: $("#s" + b.dataset.id).value, note: $("#n" + b.dataset.id).value }); render(); }; });
}, "leads");
