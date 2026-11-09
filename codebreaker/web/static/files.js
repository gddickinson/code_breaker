/* File Inspector: identify and open any file, and look inside it. Files stay on this computer. */
const FI = { data: null, name: "" };

function fiMarkdown(md) {
  const inline = s => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/\*([^*]+)\*/g, "<i>$1</i>").replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  return md.split("\n").map(l => l.startsWith("## ") ? `<h4>${inline(l.slice(3))}</h4>` : l.startsWith("# ") ? `<h3>${inline(l.slice(2))}</h3>` : l.startsWith("- ") ? `<p style="margin:2px 0">• ${inline(l.slice(2))}</p>` : l.trim() ? `<p>${inline(l)}</p>` : "").join("");
}

function fiView(v) {
  const facts = Object.keys(v.facts || {}).length ? table(Object.keys(v.facts), [Object.values(v.facts).map(String)]) : "";
  if (v.view === "image") return `${facts}<img src="${v.src}" alt="Preview of the file" style="max-width:100%;background:#fff">`;
  if (v.view === "table") return `${facts}${table(v.header, v.rows.map(r => r.map(String)))}`;
  if (v.view === "tables") return `${facts}${v.tables.map(t => `<h4>${esc(t.name)} <span class="mute">${t.rows_total} rows</span></h4>${table(t.header, t.rows)}`).join("")}`;
  if (v.view === "text") return `${facts}<pre style="max-height:420px;overflow:auto">${esc(v.text)}</pre>`;
  if (v.view === "wave") { const m = Math.max(1, ...v.envelope); return `${facts}<div class="cbars" role="img" aria-label="Loudness over time">${v.envelope.map(x => `<i style="height:${Math.max(2, x / m * 100)}%"></i>`).join("")}</div>`; }
  return facts || '<p class="mute">No built-in view for this kind, so use the byte-level views below.</p>';
}

function fiShow(r) {
  const risk = { clean: "good", suspicious: "partial", dangerous: "none" }[r.risk] || "none";
  const maxE = 8;
  $("#fiOut").innerHTML = `<div class="panel cverdict ${risk === "good" ? "readable" : risk}"><h3>${esc(r.description || r.kind)}</h3><p>${table(["File", "Size", "Detected as", "How", "Entropy (bits/byte)", "Security scan"], [[r.name, r.size_human, r.kind, r.via, r.entropy, r.risk]])}</p>
      ${r.findings.length ? table(["Severity", "Check", "Finding"], r.findings.map(f => [f.severity, f.category, f.description])) : ""}
      ${r.next.map((n, i) => n.action ? `<button class="fiNext" data-i="${i}">${esc(n.label)}</button>` : `<p class="mute">${esc(n.label)}</p>`).join(" ")}</div>
    <div class="panel"><h3>Contents</h3>${fiView(r.view)}</div>
    <div class="two"><div class="panel"><h3>Entropy through the file</h3><p class="mute">Each bar is one slice. Near 8 is compressed or encrypted; low is text, tables or padding.</p><div class="cbars" role="img" aria-label="Entropy by position in the file">${r.entropy_map.map((e, i) => `<i class="${e > 7.5 ? "top" : ""}" style="height:${Math.max(2, e / maxE * 100)}%" title="Slice ${i + 1}: ${e} bits per byte"></i>`).join("")}</div></div>
      <div class="panel"><h3>Files hidden inside</h3>${r.embedded.length ? table(["Offset", "Signature", "What it is"], r.embedded.map(e => [`${e.offset} (0x${e.offset.toString(16)})`, e.kind, e.description])) : '<p class="mute">No known file signatures after the start.</p>'}</div></div>
    <div class="two"><div class="panel"><h3>Readable strings</h3><input id="fiQ" placeholder="Filter strings" aria-label="Filter strings"><div id="fiS"></div></div><div class="panel"><h3>First bytes</h3><pre style="font-size:12px;overflow:auto">${esc(r.hex)}</pre></div></div>
    ${r.format ? `<div class="panel"><h3>From the file-format database</h3>${fiMarkdown(r.format)}</div>` : ""}`;
  const showS = () => { const q = $("#fiQ").value.toLowerCase(), s = r.strings.filter(x => x.text.toLowerCase().includes(q)).slice(0, 120); $("#fiS").innerHTML = s.length ? table(["Offset", "Text"], s.map(x => [x.offset, x.text])) : '<p class="mute">None.</p>'; };
  $("#fiQ").oninput = showS; showS();
  document.querySelectorAll(".fiNext").forEach(b => { b.onclick = () => { const n = r.next[+b.dataset.i]; if (n.action === "workbench") { window.PENDING_TEXT = r.text_for_workbench; location.hash = "#/workbench"; } if (n.action === "signals") { window.PENDING_SIGNAL = { data: FI.data, name: r.name }; location.hash = "#/signals"; } }; });
}

route(/^\/files$/, async () => {
  view().innerHTML = `<p class="kicker">// FILES</p><h1>File Inspector</h1><p class="lead">Identify and open any file. It is recognised from its first bytes rather than its name, checked for risks, and opened where possible. Hidden files inside it are listed too.</p>
    <div class="panel" id="fiDrop"><label class="filebtn">Choose a file<input id="fiFile" type="file"></label> <span class="mute">or drop one here. Up to 32 MB; the file is read on this computer and not stored.</span><p id="fiMsg" aria-live="polite"></p></div><div id="fiOut"></div>
    <div class="panel"><h3>Look up a format</h3><input id="fiF" placeholder="Name or extension, such as .fits or parquet" aria-label="Search the format database"><div id="fiFR"></div></div>`;
  const load = f => busy($("#fiFile").parentElement, $("#fiMsg"), async () => {
    if (f.size > 32 * 1024 * 1024) throw new Error("That file is too large here (32 MB limit).");
    $("#fiMsg").textContent = `Reading ${f.name}…`;
    FI.data = await new Promise((ok, no) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = no; r.readAsDataURL(f); });
    FI.name = f.name;
    fiShow(await api("/files/inspect", { name: f.name, data: FI.data }));
    $("#fiMsg").textContent = "";
  });
  $("#fiFile").onchange = e => { if (e.target.files[0]) load(e.target.files[0]); };
  const d = $("#fiDrop");
  d.ondragover = e => { e.preventDefault(); d.style.outline = "2px dashed var(--accent)"; };
  d.ondragleave = () => { d.style.outline = ""; };
  d.ondrop = e => { e.preventDefault(); d.style.outline = ""; if (e.dataTransfer.files[0]) load(e.dataTransfer.files[0]); };
  $("#fiF").oninput = async () => { const q = $("#fiF").value.trim(); if (q.length < 2) { $("#fiFR").innerHTML = ""; return; } const rows = await api(`/files/formats?q=${encodeURIComponent(q)}`); $("#fiFR").innerHTML = table(["Format", "Extensions", "Category"], rows.map(x => [x.name, x.extensions.join(" "), x.category])); };
}, "files");
