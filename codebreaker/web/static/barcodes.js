/* Barcodes & QR: make codes, read them from a picture or the camera, see a QR code's parts, and test its error correction. */
let bcStream = null, bcLast = null;

function bcStopCam() { if (bcStream) { bcStream.getTracks().forEach(t => t.stop()); bcStream = null; } }

function bcLegend() {
  return `<ul class="mute" style="list-style:none;padding:0">${BC_QR_PARTS.map(([n, c, d]) => `<li><span style="display:inline-block;width:12px;height:12px;background:${c};margin-right:6px;vertical-align:middle"></span><b>${esc(n)}</b>: ${esc(d)}</li>`).join("")}</ul>`;
}

function bcShowMade(r) {
  bcLast = r.image;
  const rb = r.read_back.length ? `Read back by zxing-cpp as <b>${esc(r.read_back[0].format)}</b>: “${esc(r.read_back[0].text)}”${r.read_back[0].ec_level ? `, error level ${esc(r.read_back[0].ec_level)}` : ""}.` : "<span class=\"err\">The reader could not read it back.</span>";
  let extra = "";
  if (r.anatomy) {
    const a = r.anatomy;
    extra = `<div class="panel"><h3>Inside this QR code</h3><p>Version ${a.version} (${a.size}×${a.size} modules), error level ${esc(a.error_level)}, mask ${a.mask}, ${esc(a.mode)} mode. Dark modules are drawn dark and light ones pale, in the colour of their part.</p>
      <img src="${a.image}" alt="The QR code with its parts coloured" style="image-rendering:pixelated;max-width:100%;width:${Math.min(480, a.size * 12)}px">
      ${table(["Part", "Modules"], Object.entries(a.modules).filter(([, v]) => v).map(([k, v]) => [k, v]))}${bcLegend()}</div>`;
  }
  if (r.check) {
    const c = r.check;
    extra = `<div class="panel"><h3>The check digit</h3><p>Multiply the digits alternately by 1 and 3, add them up, and choose the digit that brings the total to a multiple of 10. A single wrong digit, and most swaps of neighbouring digits, change the total and are caught.</p>
      ${table(["Position", "Digit", "Weight", "Product"], c.rows)}<p>Total ${c.total}; next multiple of 10 needs <b>${c.check}</b>, so the full code is <b>${esc(c.code)}</b>.</p><p>${esc(c.note)} L and G codes for the same digit are mirror images with opposite parity, which also tells the scanner which way it is reading.</p></div>`;
  }
  $("#bcMade").innerHTML = `<div class="panel"><img id="bcImg" src="${r.image}" alt="The ${esc(r.kind)} just made" style="image-rendering:pixelated;max-width:100%;background:#fff;padding:6px"><p>${rb}</p><p><a href="${r.image}" download="${esc(r.kind.replace(/\W+/g, "_"))}.png">Save as PNG</a> · <button class="alt" id="bcReadMade">Read it with the reader below</button></p></div>${extra}`;
  $("#bcReadMade").onclick = () => bcRead(r.image);
}

function bcShowRead(r) {
  const own = r.own_ean.length ? `<p>The app's own EAN-13 reader, which checks every digit's bar pattern and the check digit, also found: <b>${r.own_ean.map(esc).join(", ")}</b>.</p>` : "";
  $("#bcReadOut").innerHTML = r.codes.length
    ? `<div class="panel">${table(["Code", "Text", "Error level", "Check digit", "Symbology identifier"], r.codes.map(c => [c.format, c.text, c.ec_level || "", c.check_digit_ok === undefined ? "" : c.check_digit_ok ? "correct" : "wrong", c.symbology]))}${own}<p class="mute">Image ${r.size[0]}×${r.size[1]} pixels.</p></div>`
    : `<div class="panel"><p>No code found in this picture.${own ? "" : " Try a sharper, closer, flatter picture with a margin of blank space around the code."}</p>${own}</div>`;
}

async function bcRead(dataUrl) {
  $("#bcReadOut").innerHTML = '<p class="mute">Reading…</p>';
  try { bcShowRead(await api("/codes/read", { image: dataUrl })); } catch (e) { $("#bcReadOut").innerHTML = `<p class="err">${esc(e.message)}</p>`; }
}

function bcDamageChart(d) {
  const W = 640, H = 300, L = 50, R = 20, T = 20, B = 40, xs = d.shares, xmax = xs[xs.length - 1];
  const x = v => L + v / xmax * (W - L - R), y = v => H - B - v * (H - T - B);
  const cols = { L: "var(--c1)", M: "var(--c2)", Q: "var(--c3)", H: "var(--c4)" };
  const grid = [0, 0.5, 1].map(v => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${L - 6}" y="${y(v) + 4}" text-anchor="end" fill="var(--mute)" font-size="11">${v * 100}%</text>`).join("")
    + xs.map(v => `<text x="${x(v)}" y="${H - B + 16}" text-anchor="middle" fill="var(--mute)" font-size="11">${Math.round(v * 100)}%</text>`).join("");
  const lines = Object.entries(d.levels).map(([k, v]) => `<polyline fill="none" stroke="${cols[k]}" stroke-width="2" points="${v.rates.map((r, i) => `${x(xs[i])},${y(r)}`).join(" ")}"/>${v.rates.map((r, i) => `<circle cx="${x(xs[i])}" cy="${y(r)}" r="4" fill="${cols[k]}" stroke="var(--panel)" stroke-width="2"><title>Level ${k}: ${Math.round(r * 100)}% read with ${Math.round(xs[i] * 100)}% covered</title></circle>`).join("")}`).join("");
  const legend = Object.keys(d.levels).map(k => `<span style="margin-right:14px"><span style="display:inline-block;width:14px;height:3px;background:${cols[k]};vertical-align:middle;margin-right:5px"></span>Level ${k}</span>`).join("");
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%" role="img" aria-label="Share of damaged QR codes read, by error-correction level">${grid}${lines}<text x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle" fill="var(--mute)" font-size="12">Share of the symbol covered by the blot</text></svg><p>${legend}</p>`;
}

async function bcDamage() {
  const d = await api(`/codes/damage?text=${encodeURIComponent($("#bcDText").value)}&seed=${+$("#bcDSeed").value || 1}`);
  $("#bcDamageOut").innerHTML = `<div class="panel">${bcDamageChart(d)}
    ${table(["Level", "Version used", "Largest blot read in at least half the trials", "Nominal recovery"], Object.entries(d.levels).map(([k, v]) => [k, v.version, `${Math.round(v.largest_read * 100)}% of the symbol`, `about ${Math.round(d.nominal[k] * 100)}% of codewords`]))}
    <p class="mute">Control: the undamaged code ${d.clean_read ? "was" : "was NOT"} read. Each point is 8 random placements of a square of random noise, kept clear of the three finder patterns. The blot covers modules, not codewords, and noise leaves about half the covered modules right by chance, so the figures are not the nominal percentages: what to compare is the order of the levels.</p></div>`;
}

route(/^\/barcodes$/, async () => {
  bcStopCam();
  view().innerHTML = `<p class="kicker">// BARCODES & QR</p><h1>Barcodes and QR codes</h1><p class="lead">Codes meant to be read by machines, not hidden from people: anyone can read them. What makes them interesting is how they are found in a picture, how they protect themselves against misreading, and how much damage they survive.</p>
    <h2>Make a code</h2><div class="panel"><div class="row"><div><label for="bcKind">Kind</label><select id="bcKind"></select></div><div><label for="bcEc">Error correction</label><select id="bcEc"><option>L</option><option selected>M</option><option>Q</option><option>H</option></select></div></div>
    <label for="bcText">Text</label><input id="bcText"><p id="bcUse" class="mute"></p><button id="bcMake">Make it</button><p id="bcMsg" aria-live="polite"></p></div><div id="bcMade"></div>
    <h2>Read a code</h2><div class="panel"><p>From a photo or the camera. The server reads QR, Micro QR, Data Matrix, Aztec, MaxiCode, PDF417 and the linear codes with zxing-cpp; EAN-13 is also read by the app's own scanline reader as a cross-check.</p>
    <label class="filebtn">Choose a picture<input id="bcFile" type="file" accept="image/*"></label> <button id="bcCam" class="alt">Start camera</button> <button id="bcSnap" class="alt" disabled>Read from camera</button>
    <div class="scanbox wide" id="bcBox" hidden><video id="bcVid" playsinline muted></video></div><div id="bcReadOut" aria-live="polite"></div></div>
    <h2>Damage test</h2><div class="panel"><p>The same text is made at each error-correction level, then a growing square of noise is laid over it and the reader tries again.</p>
    <div class="row"><div><label for="bcDText">Text</label><input id="bcDText" value="https://example.org/code-breaker"></div><div><label for="bcDSeed">Seed</label><input id="bcDSeed" type="number" min="1" value="1"></div></div><button id="bcDGo">Run the damage test</button><p id="bcDMsg" aria-live="polite"></p><div id="bcDamageOut"></div></div>
    <div id="bcInfo">${bcInfoHtml()}</div>`;
  const kinds = await api("/codes/kinds"), sel = $("#bcKind");
  sel.innerHTML = kinds.map(k => `<option>${esc(k.kind)}</option>`).join("");
  const pick = () => { const k = kinds.find(x => x.kind === sel.value); $("#bcText").value = k.example; $("#bcUse").textContent = `${k.family === "matrix" ? "2D matrix code" : k.family === "stacked" ? "Stacked code" : "Linear code"}. ${k.use}`; $("#bcEc").disabled = !k.ec; };
  sel.onchange = pick; pick();
  $("#bcMake").onclick = ev => busy(ev.target, $("#bcMsg"), async () => { $("#bcMsg").textContent = ""; bcShowMade(await api("/codes/make", { kind: sel.value, text: $("#bcText").value, ec: $("#bcEc").value })); });
  $("#bcFile").onchange = e => { const f = e.target.files[0]; if (!f) return; const r = new FileReader(); r.onload = () => bcRead(r.result); r.readAsDataURL(f); };
  $("#bcCam").onclick = async () => {
    if (bcStream) { bcStopCam(); $("#bcBox").hidden = true; $("#bcSnap").disabled = true; $("#bcCam").textContent = "Start camera"; return; }
    try { bcStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment", width: 1280 } }); $("#bcVid").srcObject = bcStream; await $("#bcVid").play(); $("#bcBox").hidden = false; $("#bcSnap").disabled = false; $("#bcCam").textContent = "Stop camera"; }
    catch (e) { $("#bcReadOut").innerHTML = `<p class="err">The camera could not be opened: ${esc(e.message)}</p>`; }
  };
  $("#bcSnap").onclick = () => { const v = $("#bcVid"), c = document.createElement("canvas"); c.width = v.videoWidth; c.height = v.videoHeight; c.getContext("2d").drawImage(v, 0, 0); bcRead(c.toDataURL("image/png")); };
  $("#bcDGo").onclick = ev => busy(ev.target, $("#bcDMsg"), bcDamage);
  window.addEventListener("hashchange", bcStopCam, { once: true });
}, "barcodes");
