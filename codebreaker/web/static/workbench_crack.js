/* Workbench: streams the stages of a crack as they finish, and saves codes for the hunter. */
const CK_LANG = { en: "English", fr: "French", de: "German", it: "Italian", es: "Spanish", la: "Latin" };
const CK_PCT = v => `${Math.round(v * 100)}%`;
let WBRUN = null;

function ckBars(bars, topN = 1, low = false) {
  const vals = bars.map(b => b.value), min = Math.min(...vals), max = Math.max(...vals), span = max - min || 1;
  const order = [...vals].sort((a, b) => low ? a - b : b - a).slice(0, topN);
  const base = min < 0 ? v => (v - min) / span : v => v / (max || 1);
  return `<div class="cbars" role="img" aria-label="Bar chart of the scores">${bars.map(b => `<i class="${order.includes(b.value) ? "top" : ""}" style="height:${Math.max(3, base(b.value) * 100)}%" title="${esc(b.label)}: ${b.value}"></i>`).join("")}</div><div class="cbarlab">${bars.map(b => `<span>${esc(b.label)}</span>`).join("")}</div>`;
}

/* The same order as the server: exact decodings, then readings long enough to trust, then quality. */
function ckBetter(x, y) { return (!!y.decoded - !!x.decoded) || ((y.trusted !== false) - (x.trusted !== false)) || (y.coverage - x.coverage) || (y.score - x.score) || ((x.rank ?? 99) - (y.rank ?? 99)); }

function ckStepBody(s) {
  if (s.id === "inspect") return `${table(["Letters", "Digits", "Other", "Groups"], [[s.info.kinds.letters, s.info.kinds.digits, s.info.kinds.other, s.info.groups]])}${s.info.notes.map(n => `<p class="mute">${esc(n)}</p>`).join("")}`;
  if (s.id === "plain") return s.rows.length ? table(["Language", "Word coverage", "Letter score"], s.rows.map(r => [r.name, CK_PCT(r.coverage), r.score])) : "";
  if (s.id === "layer") return s.found.map(f => `<pre>${esc(f.text.slice(0, 300))}</pre>`).join("");
  if (s.id === "encodings") return s.found.map(f => `<p><b>${esc(f.name)}</b></p><pre>${esc(f.text.slice(0, 300))}</pre>`).join("");
  if (s.id === "stats") return `<p class="mute">${esc(s.bars_title)}. A clear peak suggests the key length.</p>${ckBars(s.bars)}${Object.keys(s.kasiski).length ? `<h4>Repeated sequences (Kasiski)</h4>${table(["Factor", "Support"], Object.entries(s.kasiski))}` : ""}`;
  if (s.id === "language") return table(["Language", "Score"], s.rows.map(r => [r.name, r.score]));
  if (s.id === "identify") return `<div class="two"><div>${table(["Rule-based guess", "Evidence"], s.rules.map(r => [r.family, r.evidence]))}</div><div>${s.network.length ? table(["Neural network guess", "Probability"], s.network.slice(0, 6).map(g => [g.name, CK_PCT(g.probability)])) : '<p class="mute">Too short for the neural network.</p>'}</div></div>`;
  return "";
}

function ckTraceBody(t) {
  const d = t.data;
  if (t.name === "frequency") return { title: "First attempt: match letter frequencies", summary: `Map the commonest cipher letters onto the commonest in ${CK_LANG[t.lang]}. This rarely gives the answer, but it shows the starting point.`, body: `${table(["Cipher letter", "Count", "First guess"], d.pairs.map(p => [p.cipher, p.count, p.plain]))}<pre>${esc(d.text)}</pre>` };
  if (t.name === "caesar") return { title: "Worked attack: all 26 Caesar shifts", summary: `Score every shift as ${CK_LANG[t.lang]}. Best: shift ${d.best}.`, body: `${ckBars(d.bars)}${table(["Shift", "Score", "Start of the text"], d.top.map(x => [x.shift, x.score, x.text]))}` };
  if (t.name === "vigenere") return { title: "Worked attack: split by key length", summary: `Taking key length ${d.period}, each position is its own Caesar cipher. Key found: ${d.key}.`, body: `${table(["Position", "Letters", "Shift", "Key letter", "Fit"], d.columns.map(c => [c.position, c.letters, c.shift, c.key, c.fit]))}<pre>${esc(d.text)}</pre>` };
  if (t.name === "climb") return { title: "Worked attack: annealing a substitution key", summary: "The same solver, stopped early and then given longer, shows the reading emerging.", body: table(["Iterations", "Score", "Text so far"], d.map(x => [x.iterations.toLocaleString(), x.score, x.text])) };
  return { title: t.name, summary: "", body: "" };
}

function ckAddStep(title, summary, body) {
  WBRUN.n++;
  $("#ckSteps").insertAdjacentHTML("beforeend", `<div class="panel cstep"><b>${WBRUN.n}</b><div class="cbody"><h3>${esc(title)}</h3><p>${esc(summary)}</p>${body}</div></div>`);
}

function ckRank() {
  const a = [...WBRUN.attempts].sort((x, y) => ckBetter(x, y));
  const rows = a.slice(0, WBRUN.showAll ? 400 : 15);
  $("#ckTable").innerHTML = `<div class="scroll"><table><thead><tr><th>Method</th><th>Family</th><th>Language</th><th>Word coverage</th><th>Score</th><th>Start of reading</th></tr></thead><tbody>${rows.map(r => `<tr class="pick ${WBRUN.sel === r ? "on" : ""}" tabindex="0" data-i="${WBRUN.attempts.indexOf(r)}"><td>${esc(r.cipher)}</td><td>${esc(r.family)}</td><td>${esc(CK_LANG[r.lang] || r.lang)}</td><td>${CK_PCT(r.coverage)}</td><td>${r.score}</td><td>${r.trusted === false ? '<span class="mute">[too short to trust] </span>' : ""}${esc(r.spaced.slice(0, 54))}</td></tr>`).join("")}</tbody></table></div>${a.length > 15 ? `<button id="ckAll" class="alt">${WBRUN.showAll ? "Show top 15" : `Show all ${a.length}`}</button>` : ""}`;
  document.querySelectorAll("#ckTable tr.pick").forEach(tr => { const open = () => { WBRUN.sel = WBRUN.attempts[+tr.dataset.i]; ckShow(WBRUN.sel); ckRank(); }; tr.onclick = open; tr.onkeydown = e => { if (e.key === "Enter") open(); }; });
  if ($("#ckAll")) $("#ckAll").onclick = () => { WBRUN.showAll = !WBRUN.showAll; ckRank(); };
}

function ckShow(r) {
  const link = r.cid ? ` <a href="#/cipher/${esc(r.cid)}">How this cipher works</a>` : "";
  const weak = !r.decoded && (r.trusted === false || r.coverage < 0.5);
  $("#ckBest").innerHTML = `${weak ? '<p class="err">Not convincing. This is only the closest attempt so far, and it may be meaningless.</p>' : ""}<h3>${esc(r.cipher)} <span class="mute">in ${esc(CK_LANG[r.lang] || r.lang)}</span></h3><pre>${esc(r.spaced)}</pre><p><b>Method:</b> ${esc(r.method || "")}${link}</p>${r.key && r.key !== "None" ? `<p><b>Key:</b> <code>${esc(r.key)}</code></p>` : ""}<p class="mute">Word coverage ${CK_PCT(r.coverage)}, letter score ${r.score}${r.seconds ? `, ${r.seconds} s` : ""}.</p>`;
}

function ckEvent(e) {
  if (e.event === "step") { ckAddStep(e.title, e.summary, ckStepBody(e)); if (e.planned) WBRUN.planned = e.planned; }
  else if (e.event === "trace") { const t = ckTraceBody(e); ckAddStep(t.title, t.summary, t.body); }
  else if (e.event === "attempt") {
    WBRUN.attempts.push(e);
    const best = WBRUN.attempts.reduce((a, b) => (ckBetter(b, a) < 0 ? b : a));
    if (!WBRUN.sel || WBRUN.autoFollow) { WBRUN.autoFollow = true; WBRUN.sel = best; ckShow(best); }
    ckRank();
    $("#ckNow").textContent = `${WBRUN.attempts.length} readings so far. Latest: ${e.cipher} in ${CK_LANG[e.lang] || e.lang}.`;
  } else if (e.event === "finish") {
    WBRUN.result = e;
    $("#ckVerdict").className = `panel cverdict ${e.verdict.level}`;
    $("#ckVerdict").innerHTML = `<h3>${esc(e.verdict.label)}</h3><p>${esc(e.verdict.why)}</p><p class="mute">${e.tried} attempts in ${e.seconds} s: ${e.readings} gave a reading, ${e.not_applicable} could not apply${e.unfinished ? `, and ${e.unfinished} planned attempts ran out of time. Allow longer to run them` : ""}.</p>`;
    submitState(e);
  } else if (e.event === "error") { $("#ckNow").innerHTML = `<span class="err">${esc(e.message)}</span>`; }
}

async function ckRun(text, budget, lang) {
  WBRUN = { n: 0, attempts: [], sel: null, autoFollow: false, showAll: false, planned: 0, result: null, ctl: new AbortController(), started: Date.now(), budget };
  $("#abo").innerHTML = `<div class="panel" id="ckVerdict"><h3>Working…</h3><p id="ckNow" aria-live="polite">Starting the attack.</p><div class="crackbar"><i id="ckProg"></i></div></div><div class="panel"><h3>Closest reading so far</h3><div id="ckBest"><p class="mute">Nothing yet.</p></div><h3>All readings, best first</h3><div id="ckTable"></div></div><h2>The steps</h2><div id="ckSteps"></div>`;
  const tick = setInterval(() => { const p = $("#ckProg"); if (p) p.style.width = `${Math.min(100, (Date.now() - WBRUN.started) / (budget * 10))}%`; }, 300);
  try {
    const res = await fetch("/api/crack", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, budget, lang: lang || null }), signal: WBRUN.ctl.signal });
    if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || `Request failed (${res.status})`); }
    const reader = res.body.getReader(), dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop();
      lines.forEach(l => { if (l.trim()) ckEvent(JSON.parse(l)); });
    }
  } finally { clearInterval(tick); }
}

function crackSetup() {
  const go = $("#crack"), stop = $("#stop");
  const leave = () => { if (!location.hash.startsWith("#/workbench") && WBRUN) { WBRUN.ctl.abort(); removeEventListener("hashchange", leave); } };
  addEventListener("hashchange", leave);
  go.onclick = async () => {
    go.disabled = true; stop.disabled = false; go.textContent = "Cracking…";
    try { await ckRun($("#t").value, +$("#cb").value, $("#cl").value); }
    catch (e) { if (e.name === "AbortError") { if ($("#ckNow")) $("#ckNow").textContent = "Stopped. The readings found so far are shown below."; const v = $("#ckVerdict"); if (v && v.querySelector("h3")) v.querySelector("h3").textContent = "Stopped"; } else $("#abo").innerHTML = `<p class="err">${esc(e.message)}</p>`; }
    finally { go.disabled = false; stop.disabled = true; go.textContent = "Crack it"; }
  };
  stop.onclick = () => { if (WBRUN) WBRUN.ctl.abort(); };
}

function submitPanel() {
  return `<div class="panel"><h3>Send a hard code to the hunter</h3><p class="mute">For codes the Workbench cannot read. The text is saved exactly as pasted, the hunter keeps working on it in its regular runs, and anything readable appears on the Lead Board.</p><p id="sState" class="reading">Run Crack it first.</p>
    <div class="row"><div><label for="sN">Name</label><input id="sN" placeholder="For example, Grandfather's postcard"></div><div><label for="sS">Where it came from</label><input id="sS" placeholder="Book, website or photo"></div></div>
    <label for="sM">Notes</label><input id="sM" placeholder="Anything known about it"><p id="sBest" class="mute"></p><button id="sGo" disabled>Add to database</button><p id="sMsg" aria-live="polite"></p><div id="sList"></div></div>`;
}

async function submitList() {
  const rows = await api("/submissions");
  $("#sList").innerHTML = rows.length ? `<h3>Your submitted codes</h3><div class="scroll"><table><thead><tr><th>Code</th><th>Symbols</th><th>Avenues</th><th>Hunter runs</th><th>Leads</th></tr></thead><tbody>${rows.map(r => `<tr><td><a href="#/lead/${esc(r.slug)}">${esc(r.name)}</a></td><td>${r.symbols}</td><td>${r.avenues}</td><td>${r.runs}</td><td>${r.leads}</td></tr>`).join("")}</tbody></table></div>` : "";
}

function submitState(end) {
  const can = end && end.verdict.level !== "readable", best = end && end.best;
  if ($("#sGo")) $("#sGo").disabled = !can;
  if ($("#sState")) $("#sState").textContent = !end ? "Run Crack it first." : can ? "The Workbench could not verify a reading, so this code can be added." : "Solved here, so there is no need to submit it.";
  if ($("#sBest")) $("#sBest").textContent = can && best && end.verdict.level === "partial" ? `The possible reading (${best.cipher}) will be saved as a lead to review.` : "";
}

function submitSetup() {
  submitList().catch(() => {});
  $("#t").addEventListener("input", () => { if (WBRUN) WBRUN.result = null; submitState(null); });
  $("#sGo").onclick = ev => busy(ev.target, $("#sMsg"), async () => {
    const b = WBRUN && WBRUN.result && WBRUN.result.best, v = WBRUN && WBRUN.result && WBRUN.result.verdict;
    const r = await api("/submissions", { name: $("#sN").value, text: $("#t").value, source: $("#sS").value, notes: $("#sM").value, best: b && v && v.level !== "none" ? { cipher: b.cipher, lang: b.lang, coverage: b.coverage, reading: b.spaced, verdict: v.label } : null });
    $("#sMsg").innerHTML = r.status === "solved" ? esc(r.message) : r.status === "duplicate" ? `This text is already tracked as <a href="#/lead/${esc(r.slug)}">${esc(r.name)}</a>, so nothing was added.` : `Added <a href="#/lead/${esc(r.slug)}">${esc(r.name)}</a>. ${r.layers && r.layers.length ? `${esc(r.layers.join(" then "))} was removed first, so the hunter works on the text inside. ` : ""}${r.hunted ? `${r.avenues} avenues are queued for the hunter's next run.` : "It is too short for the hunter (20 symbols minimum), so it is stored for reference."}`;
    await submitList();
  });
}
