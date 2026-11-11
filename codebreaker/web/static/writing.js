/* Scripts & Glyphs: read deciphered scripts sign by sign, pick signs from a palette, spell names in a script. */
let wrScripts = [], wrSigns = [];

function wrToken(t) {
  if (!t.script) return null;
  const kind = t.script === "egyptian" ? (t.kind || "") : "";
  return [t.sign, t.code || "", (t.values || []).join(", ") || "(no sound value in the tables)", kind, t.name, t.source || "Unicode name only"];
}

function wrShowRead(r) {
  const rows = r.tokens.map(wrToken).filter(Boolean);
  const unk = r.unknown ? `<p class="mute">${r.unknown} sign(s) have no sound value in the recorded tables: in Egyptian these are usually logograms (a word) or determinatives (silent classifiers), shown as [Gardiner number].</p>` : "";
  const codes = r.from_codes ? `<p class="glyphout glyph">${esc(r.from_codes)}</p>` : "";
  $("#wrOut").innerHTML = rows.length ? `<div class="panel"><h3>Transliteration</h3>${codes}<p class="glyphout">${esc(r.transliteration)}</p>
    <p>Plain letters: <b>${esc(r.simple)}</b></p><p class="mute">${r.signs} sign(s) in ${r.scripts.map(s => esc((wrScripts.find(x => x.id === s) || {}).title || s)).join(", ")}. A transliteration gives the sounds, not the meaning; Egyptian writes consonants only, so vowels are not shown.</p>${unk}
    ${table(["Sign", "Code", "Value", "Kind", "Unicode name", "Source"], rows)}<button class="alt" id="wrToCrack">Treat the plain letters as a cipher (Workbench)</button>${wrToGloss(r)}</div>`
    : `<div class="panel"><p>No signs from the supported scripts were found. Paste signs as Unicode text, or pick them from the palette.</p></div>`;
  const g = $("#wrToGloss");
  if (g) g.onclick = () => { $("#wrGLang").value = g.dataset.lang; $("#wrGText").value = g.dataset.text; $("#wrGloss").click(); $("#wrGOut").scrollIntoView({ behavior: "smooth" }); };
  const b = $("#wrToCrack");
  if (b) b.onclick = () => { sessionStorage.setItem("workbenchText", r.simple); location.hash = "#/workbench"; };
}

async function wrDoGloss() {
  const r = await api("/writing/gloss", { text: $("#wrGText").value, lang: $("#wrGLang").value });
  const rows = r.words.map(w => [w.word, w.found ? w.senses.map(s => `${s.pos ? s.pos.toLowerCase() + ": " : ""}${s.sense}${s.labels.length ? " (" + s.labels.join("; ") + ")" : ""}`).join(" | ") : "not in the word list"]);
  $("#wrGOut").innerHTML = `<div class="panel">${table(["Word", "Dictionary senses"], rows)}<p class="mute">${r.found} of ${r.of} words found. ${esc(r.note)} Source: ${esc(r.source)}.</p></div>`;
}

function wrToGloss(r) {
  const lang = r.scripts.includes("egyptian") ? "egyptian" : r.scripts.includes("linear_b") ? "mycenaean" : r.scripts.includes("runic") ? "old_norse" : null;
  if (!lang) return "";
  const text = lang === "egyptian" ? r.transliteration.replace(/\[[^\]]*\]/g, "").replace(/\./g, "") : r.tokens.map(t => t.sign).join("");
  return `<button class="alt" id="wrToGloss" data-lang="${lang}" data-text="${esc(text)}">Gloss these words</button>`;
}

function wrPalette() {
  const q = $("#wrFind").value.trim().toLowerCase();
  const list = wrSigns.filter(s => !q || s.values.some(v => v.toLowerCase().includes(q)) || s.code.toLowerCase() === q || s.name.toLowerCase().includes(q)).slice(0, 400);
  $("#wrPal").innerHTML = list.map((s, i) => `<button class="glyph" data-i="${i}" title="${esc(s.name)}${s.code ? " (" + esc(s.code) + ")" : ""}: ${esc(s.values.join(", ") || "no sound value")}">${esc(s.sign)}<small>${esc(s.values[0] || s.code || "·")}</small></button>`).join("")
    || '<p class="mute">No sign matches.</p>';
  $("#wrPal").querySelectorAll("button").forEach(b => b.onclick = () => { const ta = $("#wrText"); ta.value += list[+b.dataset.i].sign; ta.focus(); });
  $("#wrPalNote").textContent = `${list.length} of ${wrSigns.length} signs shown${list.length === 400 ? " (narrow the search to see more)" : ""}.`;
}

async function wrLoadPalette() {
  wrSigns = await api(`/writing/signs/${$("#wrPick").value}`);
  wrPalette();
}

async function wrWrite() {
  const r = await api("/writing/write", { text: $("#wrLatin").value, script: $("#wrWScript").value });
  $("#wrWOut").innerHTML = `<div class="panel"><p class="glyphout glyph">${esc(r.text)}</p><p class="mute">${esc(r.note)}${r.substitutions.length ? " Letters the script lacks: " + esc(r.substitutions.join("; ")) + "." : ""}</p>
    <button class="alt" id="wrBack">Read it back above</button></div>`;
  $("#wrBack").onclick = () => { $("#wrText").value = r.text; $("#wrRead").click(); };
}

route(/^\/scripts$/, async () => {
  wrScripts = await api("/writing/scripts");
  const opts = wrScripts.map(s => `<option value="${s.id}">${esc(s.title)} (${s.signs} signs, ${s.with_value} with a value)</option>`).join("");
  view().innerHTML = `<p class="kicker">// SCRIPTS & GLYPHS</p><h1>Scripts and glyphs</h1>
    <p class="lead">Read writing systems that have been deciphered, sign by sign: Egyptian hieroglyphs, Linear B, runes, Ogham, Phoenician, Gothic, Ugaritic, Old Persian and cuneiform sign names. Every value comes from a recorded source, named in the table.</p>
    <p class="mute">Reading the sounds is not translating. For Egyptian, Mycenaean Greek and Old Norse the page can gloss words from a dictionary below, which is still not a translation. Scripts nobody can read (Linear A, rongorongo, the Phaistos Disc) are in the <a href="#/mysteries">Mystery Lab</a>'s lost-script analyses.</p>
    <h2>Read</h2><div class="panel"><label for="wrText">Signs: paste Unicode text, use the palette, or type Gardiner numbers such as <code>G1 D21 N35</code></label><textarea id="wrText" class="glyph" rows="3">ᚠᚢᚦᚨᚱᚲ ᚷᚹ</textarea>
    <button id="wrRead">Read it</button><button class="alt" id="wrClear">Clear</button><div id="wrOut" aria-live="polite"></div></div>
    <h2>Gloss the words</h2><div class="panel"><p class="mute">Dictionary meanings of each word on its own, from Wiktionary (CC BY-SA). A gloss is not a translation: grammar, word order and the choice between senses are left to you. Egyptian written without spaces is cut into dictionary words, and that cut is only one possibility.</p>
    <div class="row"><div><label for="wrGLang">Language</label><select id="wrGLang"><option value="egyptian">Egyptian (transliteration, e.g. ꜥnḫ wḏꜣ snb)</option><option value="mycenaean">Mycenaean Greek (Linear B signs)</option><option value="old_norse">Old Norse (Latin letters or runes)</option></select></div>
    <div><label for="wrGText">Words</label><input id="wrGText" class="glyph" value="ꜥnḫ wḏꜣ snb"></div></div><button id="wrGloss">Gloss</button><div id="wrGOut" aria-live="polite"></div></div>
    <h2>Sign palette</h2><div class="panel"><div class="row"><div><label for="wrPick">Script</label><select id="wrPick">${opts}</select></div>
    <div><label for="wrFind">Find by sound, Gardiner number or name</label><input id="wrFind" placeholder="e.g. nfr, G1, owl, ka"></div></div>
    <p id="wrPalNote" class="mute"></p><div id="wrPal" class="palette"></div></div>
    <h2>Write a name</h2><div class="panel"><div class="row"><div><label for="wrLatin">Latin letters</label><input id="wrLatin" value="Cleopatra"></div>
    <div><label for="wrWScript">Script</label><select id="wrWScript">${wrScripts.filter(s => s.can_write).map(s => `<option value="${s.id}">${esc(s.title)}</option>`).join("")}</select></div></div>
    <button id="wrWrite">Spell it</button><p id="wrWMsg"></p><div id="wrWOut" aria-live="polite"></div></div>`;
  $("#wrRead").onclick = ev => busy(ev.target, $("#wrOut"), async () => wrShowRead(await api("/writing/read", { text: $("#wrText").value })));
  $("#wrGloss").onclick = ev => busy(ev.target, $("#wrGOut"), wrDoGloss);
  $("#wrClear").onclick = () => { $("#wrText").value = ""; $("#wrOut").innerHTML = ""; };
  $("#wrPick").onchange = wrLoadPalette;
  $("#wrFind").oninput = wrPalette;
  $("#wrWrite").onclick = ev => busy(ev.target, $("#wrWMsg"), wrWrite);
  await wrLoadPalette();
}, "scripts");
