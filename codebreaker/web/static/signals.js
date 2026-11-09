/* Signal Workbench: turn raw bytes from a camera or sensor back into a picture. */
const SG = { data: null, info: null };
const SG_EXAMPLES = { kinect11: "Kinect depth (11-bit packed)", yuyv: "USB webcam (YUYV)", raw10: "Camera sensor (RAW10)", rgb565: "Display buffer (RGB565)", bayer: "Colour sensor (Bayer)", gray16le: "16-bit sensor" };

function sgCurve(d) {
  const W = 640, H = 150, n = d.curve.length, max = Math.max(...d.curve), min = Math.min(...d.curve);
  const x = i => 40 + i * (W - 50) / (n - 1), y = v => 10 + (1 - (v - min) / (max - min || 1)) * (H - 40);
  const at = Math.round((d.stride - d.curve_start) / d.curve_step);
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:720px" role="img" aria-label="Difference between bytes one row apart, for each row length"><polyline fill="none" stroke="var(--c1)" stroke-width="2" points="${d.curve.map((v, i) => `${x(i)},${y(v)}`).join(" ")}"/>
    <circle cx="${x(at)}" cy="${y(d.curve[at] ?? min)}" r="6" fill="var(--c2)" stroke="var(--panel)" stroke-width="2"><title>Row length ${d.stride} bytes</title></circle>
    <text x="${x(at) + 9}" y="${y(d.curve[at] ?? min) + 4}" fill="var(--ink)" font-size="12">${d.stride} bytes</text>
    <text x="40" y="${H - 6}" fill="var(--mute)" font-size="12">${d.curve_start} bytes</text><text x="${W - 10}" y="${H - 6}" fill="var(--mute)" font-size="12" text-anchor="end">${d.curve_start + d.curve_step * (n - 1)} bytes</text></svg>`;
}

function sgControls(d) {
  const b = d.best || { format: "gray8", width: 256 };
  return `<div class="row crackopts" style="max-width:none"><div><label for="sgF">Format</label><select id="sgF">${Object.entries(d.formats).map(([k, v]) => `<option value="${k}" ${k === b.format ? "selected" : ""}>${esc(v)}</option>`).join("")}</select></div>
    <div><label for="sgW">Width (pixels)</label><input id="sgW" type="number" min="2" value="${b.width}"></div><div><label for="sgO">Skip bytes at start</label><input id="sgO" type="number" min="0" value="0"></div>
    <div><label for="sgB">Bayer pattern</label><select id="sgB">${["RGGB", "BGGR", "GRBG", "GBRG"].map(p => `<option>${p}</option>`).join("")}</select></div></div><button id="sgR">Redraw</button> <button id="sgM" class="alt">Width −1</button> <button id="sgP" class="alt">Width +1</button>`;
}

async function sgRender() {
  const r = await api("/signals/raw", { data: SG.data, format: $("#sgF").value, width: +$("#sgW").value, offset: +$("#sgO").value, bayer: $("#sgB").value });
  $("#sgImg").src = r.preview;
}

async function sgAnalyse() {
  $("#sgOut").innerHTML = '<p class="mute">Measuring…</p>';
  const d = await api("/signals/raw", { data: SG.data });
  SG.info = d;
  const rel = d.reliability, best = d.best;
  const trust = best && rel[best.format] ? `In generated tests, this format and width were both found ${rel[best.format].correct} times out of ${rel[best.format].cases}.` : "";
  $("#sgOut").innerHTML = `<div class="panel cstep"><b>1</b><div class="cbody"><h3>Find the row length</h3><p>Pixels are usually similar to the pixel directly below. Comparing every byte with the byte a fixed distance later shows a dip at the length of one row: <b>${d.stride} bytes</b>.</p>${sgCurve(d)}</div></div>
    <div class="panel cstep"><b>2</b><div class="cbody"><h3>Find the pixel format</h3><p>Each format is decoded at that row length, and the smoothest picture wins. ${esc(trust)}</p>${table(["Format", "Width", "Height", "Roughness (lower is better)", "Note"], d.ranking.slice(0, 8).map(r => [r.name, r.width, r.height, r.smoothness, r.note || ""]))}
    <p class="mute">Reliable in tests: 8-bit, RAW10, Kinect 11-bit, YUYV and RGB24. Less reliable: 16-bit, RAW12 and RGB565. A Bayer mosaic is usually reported as 8-bit grey, so try the Bayer setting below if a grey picture shows a fine checkerboard.</p></div></div>
    <div class="panel cstep"><b>3</b><div class="cbody"><h3>Look, and adjust</h3><p>A slanted picture means the width is slightly wrong. A picture repeated side by side means half the true width.</p>${sgControls(d)}<div style="overflow:auto;margin-top:10px"><img id="sgImg" alt="The reconstructed frame" src="${d.preview || ""}" style="image-rendering:pixelated;max-width:100%;background:#000"></div></div></div>`;
  $("#sgR").onclick = ev => busy(ev.target, $("#sgMsg"), sgRender);
  $("#sgM").onclick = () => { $("#sgW").value = +$("#sgW").value - 1; sgRender(); };
  $("#sgP").onclick = () => { $("#sgW").value = +$("#sgW").value + 1; sgRender(); };
  $("#sgF").onchange = () => { const f = $("#sgF").value, row = d.ranking.find(r => r.format === f); if (row) $("#sgW").value = row.width; sgRender(); };
}

route(/^\/signals$/, async () => {
  view().innerHTML = `<p class="kicker">// SIGNALS</p><h1>Signal Workbench</h1><p class="lead">Raw frames from cameras and sensors arrive as bare bytes, with no width or format attached. This page finds both and rebuilds the picture.</p>
    <div class="panel"><div class="row"><div><label for="sgX">Generated example</label><select id="sgX">${Object.entries(SG_EXAMPLES).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("")}</select></div><div><label class="filebtn">Or open a raw file<input id="sgFile" type="file"></label></div></div>
    <button id="sgGo">Load example and analyse</button><p id="sgMsg" class="mute" aria-live="polite"></p></div><div id="sgOut"></div>
    <div class="panel"><h3>How a Kinect sends depth</h3><p>The Kinect for Xbox 360 measures depth by projecting a pattern of infrared dots and watching how it shifts. Each frame is 640 by 480 depth values of 11 bits, packed end to end with no padding, so 8 pixels take 11 bytes. libfreenect unpacks these into 16-bit numbers; the value 2047 marks pixels with no reading, such as shadows and the edge of the view.</p></div>`;
  $("#sgGo").onclick = ev => busy(ev.target, $("#sgMsg"), async () => {
    const e = await api(`/signals/example/${$("#sgX").value}`);
    SG.data = e.data;
    $("#sgMsg").textContent = `${e.title}: ${e.bytes.toLocaleString()} bytes, with no header. The true layout is ${e.truth.format}, ${e.truth.width} wide; see whether the analysis finds it.`;
    await sgAnalyse();
  });
  $("#sgFile").onchange = ev => busy(ev.target.parentElement, $("#sgMsg"), async () => {
    const f = ev.target.files[0];
    if (!f) return;
    if (f.size > 16 * 1024 * 1024) throw new Error("That file is too large here (16 MB limit).");
    SG.data = await new Promise((ok, no) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = no; r.readAsDataURL(f); });
    $("#sgMsg").textContent = `${f.name}: ${f.size.toLocaleString()} bytes.`;
    await sgAnalyse();
  });
}, "signals");
