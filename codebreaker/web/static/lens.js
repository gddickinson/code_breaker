/* Lens: point the camera at anything, or drop in a picture or file; read text, codes and signs, translate, and look
   for hidden messages. The overlay (lens_overlay.js) marks every finding on the view. */
let lensStream = null, lensTimer = 0, lensBusy = false, lensLog = [], lensRef = null, lensFlow = 0, lensVotes = [], lensSession = null;

/* The language shown in the live view: a majority of the last 8 frames that named one (5 needed), so one noisy
   frame cannot switch it. */
function lensLangVote(lang) {
  lensVotes = [...lensVotes, lang && lang.code ? lang.name : null].slice(-8);
  const named = lensVotes.filter(Boolean), counts = {};
  named.forEach(n => { counts[n] = (counts[n] || 0) + 1; });
  const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
  return top && top[1] >= 5 ? top[0] : "detecting language…";
}
const LENS_SMALL = 160;

/* A small grey copy of the current video frame, and the shift (in source pixels) that best aligns it with the copy
   taken when the frame was sent: boxes from the server are moved by that shift until the next reply arrives. */
function lensSmall(v) {
  const c = document.createElement("canvas"), s = LENS_SMALL / v.videoWidth;
  c.width = LENS_SMALL; c.height = Math.round(v.videoHeight * s);
  const g = c.getContext("2d", { willReadFrequently: true }); g.drawImage(v, 0, 0, c.width, c.height);
  const d = g.getImageData(0, 0, c.width, c.height).data, out = new Float32Array(c.width * c.height);
  for (let i = 0; i < out.length; i++) out[i] = d[4 * i] * 0.3 + d[4 * i + 1] * 0.59 + d[4 * i + 2] * 0.11;
  return { px: out, w: c.width, h: c.height, scale: v.videoWidth / c.width };
}

function lensShift(a, b, r = 12) {
  let best = [0, 0], bs = Infinity;
  for (let dy = -r; dy <= r; dy += 2) for (let dx = -r; dx <= r; dx += 2) {
    let s = 0, n = 0;
    for (let y = r; y < a.h - r; y += 3) for (let x = r; x < a.w - r; x += 3) { s += Math.abs(a.px[y * a.w + x] - b.px[(y + dy) * b.w + x + dx]); n++; }
    s /= n; if (s < bs) { bs = s; best = [dx, dy]; }
  }
  return best;
}

function lensLogAdd(lines) {
  const stamp = new Date().toTimeString().slice(0, 8);
  lensLog = [...lines.map(l => `${stamp}  ${l}`), ...lensLog].slice(0, 60);
  $("#lnLog").textContent = lensLog.join("\n");
}

function lensStop(keepSession = false) {
  lensVotes = []; if (!keepSession) lensSession = null;
  clearInterval(lensTimer); lensTimer = 0; clearInterval(lensFlow); lensFlow = 0; lensRef = null;
  if (lensStream) { lensStream.getTracks().forEach(t => t.stop()); lensStream = null; }
}

function lensFit(w, h) {
  const c = $("#lnCanvas"), box = $("#lnStage");
  const W = Math.min(box.clientWidth || 900, 960);
  c.width = W; c.height = Math.round(W * h / w);
}

function lensShowImage(dataUrl, cb, keepSession = false) {
  lensStop(keepSession); $("#lnVid").hidden = true;
  const img = $("#lnImg");
  img.onload = () => { img.hidden = false; lensFit(img.naturalWidth, img.naturalHeight); lensOverlayStart($("#lnCanvas")); cb && cb(img); };
  img.src = dataUrl;
}

const KIND_NAME = { text: "text", code: "code", sign: "sign", lsb: "hidden: pixel bits", trailing: "hidden: after the end", embedded: "hidden: file inside",
  metadata: "metadata", zero_width: "hidden: invisible characters", whitespace: "hidden: whitespace", homoglyph: "look-alike letters", acrostic: "acrostic" };

function lensAI(a) {  /* Round 90a: the local vision model's words, split by whether the OCR letters agree */
  if (!a.confirmed) return `<h3>Second reader</h3><p class="mute">${esc(a.mode)}. ${esc(a.note || "")}</p>`;
  return `<h3>Second reader</h3><p>Mode: <b>${esc(a.mode)}</b> (${esc(a.seconds)} s). ${esc(a.note)}</p>
    <p><b>Confirmed by the OCR letters:</b> ${esc(a.confirmed.join(" ") || "none")}</p>
    <p><b>AI only (a suggestion, may be invented):</b> <span class="mute">${esc(a.ai_only.join(" ") || "none")}</span></p>`;
}

function lensReport(r) {
  const fs = r.findings || [];
  const hidden = fs.filter(f => !["text", "code", "sign"].includes(f.kind));
  const lang = r.language ? `${esc(r.language.name)}${r.language.how === "script" ? " (by script)" : ""}` : "none found";
  const tr = r.translation ? (r.translation.text ? `<p><b>Translation:</b> ${esc(r.translation.text)}</p>` : `<p class="mute">${esc(r.translation.note || "")}</p>`) : "";
  const codes = fs.filter(f => f.kind === "code").map(f => [f.label]);
  const signs = fs.filter(f => f.kind === "sign");
  const planes = r.bit_planes ? Object.entries(r.bit_planes).map(([k, v]) => `<figure style="display:inline-block;margin:4px"><img src="${v}" alt="lowest bit plane of the ${esc(k)} channel" style="max-width:220px;image-rendering:pixelated;border:1px solid var(--line)"><figcaption class="mute">${esc(k)} lowest bits</figcaption></figure>`).join("") : "";
  $("#lnOut").innerHTML = `<div class="panel lensrep">
    ${r.text !== undefined ? `<h3>Text</h3><p>Script: <b>${esc(r.script || "?")}</b> · language: <b>${lang}</b>${r.mean_conf !== undefined ? ` · mean OCR confidence ${esc(r.mean_conf)}` : ""}</p><pre class="lenstext">${esc(r.text || "(no text read)")}</pre>${tr}
      ${r.text ? '<button class="alt" id="lnToBench">Treat it as a cipher (Workbench)</button>' : ""}` : ""}
    ${r.ai ? lensAI(r.ai) : ""}
    ${codes.length ? `<h3>Codes</h3>${table(["Code"], codes)}` : ""}
    ${signs.length ? `<h3>Signs</h3><p class="mute">Top suggestion per sign; open the Scripts page for all five and to choose.</p><p class="glyph glyphout">${signs.map(s => esc(s.detail ? s.detail[0] : "")).join(" ")}</p><button class="alt" id="lnToScripts">Read these signs (Scripts page)</button>` : ""}
    <h3>Hidden-message checks</h3>${hidden.length ? table(["Finding", "What it is", "Detail"], hidden.map(f => [KIND_NAME[f.kind] || f.kind, f.label, typeof f.detail === "string" ? f.detail.slice(0, 200) : ""])) : "<p>Nothing found by the checks that ran.</p>"}
    ${r.stego ? `<p class="mute">${esc(r.stego.caveat)}</p>` : ""}${planes ? `<details><summary>Lowest bit planes (hidden pixel data often shows as noise or a pattern here)</summary>${planes}</details>` : ""}</div>`;
  const b = $("#lnToBench"); if (b) b.onclick = () => { try { sessionStorage.setItem("workbenchText", r.text); } catch (e) { /* storage unavailable */ } location.hash = "#/workbench"; };
  const s = $("#lnToScripts"); if (s) s.onclick = () => { location.hash = "#/scripts"; setTimeout(() => { const t = $("#wrText"); if (t) { t.value = signs.map(x => x.detail[0]).join(""); $("#wrRead").click(); } }, 400); };
}

async function lensAnalyseImage(dataUrl) {
  lensLogAdd(["picture received", "full analysis: text, codes, signs, translation, hidden messages"]);
  lensOv.status = "analysing";
  const ai = !!($("#lnAI") && $("#lnAI").checked);
  if (ai) lensLogAdd(["asking the local vision model as a second reader (can take a minute)"]);
  const r = await api("/lens/image", { image: dataUrl, signs: $("#lnSigns").value, script: $("#lnScript").value || null, session: lensSession, ai });
  lensOverlaySet(r.findings, r.size[0], `${r.findings.length} findings`);
  lensLogAdd(r.log.reverse());
  lensReport(r);
}

async function lensFile(f) {
  const data = await new Promise(res => { const rd = new FileReader(); rd.onload = () => res(rd.result); rd.readAsDataURL(f); });
  if (f.type.startsWith("image/")) return lensShowImage(data, () => busy($("#lnFileBtn"), $("#lnMsg"), () => lensAnalyseImage(data)));
  lensLogAdd([`file ${f.name}, ${f.size} bytes`]);
  const r = await api("/lens/file", { name: f.name, data });
  lensLogAdd((r.log || []).reverse());
  if (r.type === "image") lensShowImage(data);
  lensReport(r);
}

async function lensLiveTick() {
  if (lensBusy || !lensStream) return;
  const v = $("#lnVid");
  if (!v.videoWidth) return;
  lensBusy = true;
  const ref = lensSmall(v);
  const c = document.createElement("canvas"), s = Math.min(1, 960 / v.videoWidth);
  c.width = v.videoWidth * s; c.height = v.videoHeight * s;
  c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
  try {
    const r = await api("/lens/image", { image: c.toDataURL("image/jpeg", 0.85), live: true, script: $("#lnScript").value || null, session: lensSession });
    if (r.session) lensSession = r.session;
    $("#lnTips").innerHTML = (r.tips || []).map(t => `<li>${esc(t)}</li>`).join("");
    lensRef = ref; lensRef.srcScale = r.size[0] / LENS_SMALL;
    lensOverlayShift(0, 0);
    lensOverlaySet(r.findings, r.size[0], r.text ? `${r.script} · ${lensLangVote(r.language)}${r.pending ? " · closer look" : ""}` : "scanning", !r.session);
    if (r.text) { $("#lnLive").textContent = r.text; lensLogAdd([`read ${r.findings.length} item(s) in ${r.script}`]); }
  } catch (e) { lensLogAdd([`error: ${e.message}`]); }
  lensBusy = false;
}

route(/^\/lens(\/demo)?$/, async demo => {
  const scripts = await api("/lens/scripts");
  const aiSt = await api("/ai/status").catch(() => ({}));
  view().innerHTML = `<p class="kicker">// LENS</p><h1>Lens</h1>
    <p class="lead">Point the camera at a sign, a page or a carving, or drop in a picture or file. The lens reads printed text in over a hundred languages and scripts, codes, and runes, hieroglyphs and other signs; translates what it can; and looks for messages hidden in the picture or the text.</p>
    <p class="mute">Translation covers the languages with an installed translator (more are coming). Hidden-message checks report what the tests measure, with their false-alarm rates; nothing is claimed as a secret message without a reading.</p>
    <div class="panel"><div class="row"><div><label for="lnScript">Script</label><select id="lnScript"><option value="">Detect automatically</option>${scripts.map(s => `<option>${esc(s)}</option>`).join("")}</select></div>
      <div id="lnAIBox" hidden><label style="display:flex;gap:8px;align-items:flex-start;margin-top:24px"><input type="checkbox" id="lnAI" style="width:auto;margin-top:3px"> Second reader: the local vision model (slower; the picture stays on this machine)</label></div>
      <div><label for="lnSigns">Runes, hieroglyphs and other signs</label><select id="lnSigns"><option value="auto">Confident signs outside the text</option><option value="always">Every sign found</option><option value="never">Never</option></select></div></div>
      <button id="lnCam">Start live camera</button> <button id="lnSnap" class="alt" disabled>Capture and analyse</button>
      <label class="filebtn" id="lnFileBtn">Upload a picture or file<input id="lnFile" type="file"></label> <button id="lnDemo" class="alt">Try a sample picture</button>
      <p id="lnMsg" aria-live="polite"></p>
      <div class="lensstage" id="lnStage"><video id="lnVid" playsinline muted hidden></video><img id="lnImg" alt="The picture being analysed" hidden><canvas id="lnCanvas" aria-hidden="true"></canvas></div>
      <p id="lnLive" class="lenslive" aria-live="polite"></p><ul id="lnTips" class="lenstips" aria-live="polite"></ul>
      <details open><summary>Scan log</summary><pre id="lnLog" class="lenslog"></pre></details>
      <label for="lnText">Or paste text to check for hidden messages and translate</label><textarea id="lnText" rows="4"></textarea><button id="lnTextGo" class="alt">Check the text</button></div>
    <div id="lnOut" aria-live="polite"></div>`;
  $("#lnCam").onclick = async () => {
    if (lensStream) { lensStop(); lensOverlayStop(); $("#lnVid").hidden = true; $("#lnSnap").disabled = true; $("#lnCam").textContent = "Start live camera"; lensLogAdd(["camera off"]); return; }
    try {
      lensStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment", width: 1280 } });
      const v = $("#lnVid"); v.srcObject = lensStream; await v.play();
      $("#lnImg").hidden = true; v.hidden = false; lensFit(v.videoWidth, v.videoHeight); lensOverlayStart($("#lnCanvas"));
      $("#lnSnap").disabled = false; $("#lnCam").textContent = "Stop camera"; lensLogAdd(["camera on", "live reading every second"]);
      lensTimer = setInterval(lensLiveTick, 900);
      lensFlow = setInterval(() => {  // move the boxes with the picture between server replies
        if (!lensRef || !lensStream) return;
        const [dx, dy] = lensShift(lensRef, lensSmall($("#lnVid")));
        lensOverlayShift(dx * lensRef.srcScale, dy * lensRef.srcScale);
      }, 120);
    } catch (e) { $("#lnMsg").innerHTML = `<span class="err">The camera could not be opened: ${esc(e.message)}</span>`; }
  };
  $("#lnSnap").onclick = ev => { const v = $("#lnVid"), c = document.createElement("canvas"); c.width = v.videoWidth; c.height = v.videoHeight; c.getContext("2d").drawImage(v, 0, 0); const d = c.toDataURL("image/png"); lensShowImage(d, () => busy(ev.target, $("#lnMsg"), () => lensAnalyseImage(d)), true); $("#lnCam").textContent = "Start live camera"; $("#lnSnap").disabled = true; };
  $("#lnFile").onchange = e => { const f = e.target.files[0]; if (f) busy($("#lnFileBtn"), $("#lnMsg"), () => lensFile(f)); };
  if (aiSt.vision) { $("#lnAIBox").hidden = false; $("#lnAI").title = `Local model ${aiSt.vision}`; }
  $("#lnTextGo").onclick = ev => busy(ev.target, $("#lnMsg"), async () => { const r = await api("/lens/text", { text: $("#lnText").value }); lensLogAdd(r.log.reverse()); lensReport(r); });
  const runDemo = async () => { const d = (await api("/lens/sample")).image; lensShowImage(d, () => busy($("#lnDemo"), $("#lnMsg"), () => lensAnalyseImage(d))); };
  $("#lnDemo").onclick = runDemo;
  window.addEventListener("hashchange", () => { lensStop(); lensOverlayStop(); }, { once: true });
  if (demo) runDemo();
  lensLogAdd(["lens ready", `${scripts.length} script models loaded`]);
}, "lens");
