/* Video Signals: rebuild a picture from sampled VGA or composite video. */
function vdTrace(t) {
  if (!t || !t.red) return "";
  const W = 900, H = 170, n = t.red.length, x = i => 20 + i / (n - 1) * (W - 40), max = Math.max(...t.red, 0.01);
  const red = t.red.map((v, i) => `${x(i)},${100 - v / max * 70}`).join(" "), sync = t.sync.map((v, i) => `${x(i)},${v ? 130 : 150}`).join(" ");
  const total = Object.values(t.parts_us).reduce((a, b) => a + b, 0), names = ["sync", "back porch", "picture", "front porch"];
  /* Place the standard's parts from where the sync pulse actually starts in this trace, one line apart. */
  const s0 = Math.max(0, t.sync.indexOf(1)), rest = t.sync.slice(s0), next = rest.findIndex((v, i) => i > 2 && v === 1 && rest[i - 1] === 0), line = next > 0 ? next : n / 2;
  const bands = [0, 1].flatMap(l => { let acc = 0; return names.map(nm => { const a0 = s0 + l * line + acc / total * line, a1 = a0 + t.parts_us[nm] / total * line; acc += t.parts_us[nm]; if (a0 >= n - 1) return ""; const xa = x(a0), xb = x(Math.min(a1, n - 1)); return `<rect x="${xa}" y="8" width="${Math.max(1, xb - xa)}" height="152" fill="${nm === "picture" ? "rgba(0,160,181,.10)" : "rgba(224,80,140,.12)"}"/>${l === 0 ? `<text x="${xa + 3}" y="${20 + names.indexOf(nm) % 2 * 13}" fill="var(--mute)" font-size="11">${esc(nm)}</text>` : ""}`; }); }).join("");
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;background:#05040e" role="img" aria-label="Two lines of the red signal and the line sync">${bands}<polyline fill="none" stroke="var(--c2)" stroke-width="1.2" points="${red}"/><polyline fill="none" stroke="var(--c1)" stroke-width="1.5" points="${sync}"/><text x="${W - 20}" y="125" text-anchor="end" fill="var(--ink)" font-size="11">line sync</text><text x="${W - 20}" y="40" text-anchor="end" fill="var(--ink)" font-size="11">red channel</text></svg><p class="mute">Shaded parts follow the published timing; the shapes on top are the measured signal.</p>`;
}

function vdShow(r) {
  const m = r.measured || {}, rel = r.reliability;
  const rows = Object.entries(m).map(([k, v]) => [k.replaceAll("_", " "), String(v)]);
  $("#vdOut").innerHTML = `<div class="panel cverdict ${r.ok ? "readable" : "none"}"><h3>${r.ok ? (r.mode ? `Recognised ${esc(r.mode)}` : "Composite picture recovered") : "Not decoded"}</h3>${r.reason ? `<p>${esc(r.reason)}</p>` : ""}<p class="mute">Sampled at ${r.fs_mhz} MHz.${r.match !== null && r.match !== undefined ? ` The rebuilt picture matches what was sent with correlation ${r.match}.` : ""}</p></div>
    <div class="two"><div class="panel"><h3>Rebuilt from the samples</h3>${r.image ? `<img src="${r.image}" alt="Picture rebuilt from the signal" style="width:100%;image-rendering:pixelated">` : '<p class="mute">No picture.</p>'}</div><div class="panel"><h3>What was sent</h3><img src="${r.sent}" alt="The original picture" style="width:100%"></div></div>
    <div class="panel"><h3>Measured</h3>${window.table(["Quantity", "Value"], rows)}${vdTrace(r.trace)}<p class="mute">Control: ${rel.decoded} of ${rel.cases} generated captures decoded, mean match ${rel.mean_match} (worst ${rel.worst_match}, composite at a low sample rate); ${rel.null_decoded} of ${rel.null_trials} noise signals were wrongly decoded.</p></div>`;
}

route(/^\/video$/, async () => {
  view().innerHTML = `<p class="kicker">// VIDEO SIGNALS</p><h1>Video signals</h1><p class="lead">An analog video signal is a picture read out line by line, with pulses marking where each line and each frame begins. Find the pulses, recognise the timing, and the picture can be rebuilt.</p>
    <div class="panel"><div class="row"><div><label for="vdK">Signal</label><select id="vdK"><option>640x480 @ 60 Hz</option><option>720x400 @ 70 Hz</option><option>800x600 @ 60 Hz</option><option>1024x768 @ 60 Hz</option><option>1280x720 @ 60 Hz</option><option value="composite">Composite video (monochrome)</option></select></div>
    <div><label for="vdF">Sample rate (times the pixel clock): <b id="vdFv"></b></label><input id="vdF" type="range" min="0.5" max="2" step="0.05" value="1"></div><div><label for="vdN">Noise: <b id="vdNv"></b></label><input id="vdN" type="range" min="0" max="0.2" step="0.01" value="0.02"></div></div>
    <button id="vdGo">Generate and decode</button><p id="vdMsg" aria-live="polite"></p></div><div id="vdOut"></div>
    <div class="biogrid"><div class="panel"><h3>VGA</h3><p>Red, green and blue travel on separate wires, with separate line and frame sync. The line rate, number of lines, sync widths and polarities identify the mode: 640x480 and 720x400 share a 31.47 kHz line rate but differ in lines per frame and sync polarity.</p></div><div class="panel"><h3>Composite</h3><p>One wire carries everything. Sync pulses dip below the blanking level; short ones start a line, broad ones start a frame. This page decodes brightness only; colour rides on a 3.58 MHz subcarrier that is not decoded here.</p></div></div>`;
  const lab = () => { $("#vdFv").textContent = `${(+$("#vdF").value).toFixed(2)}x`; $("#vdNv").textContent = (+$("#vdN").value).toFixed(2); };
  $("#vdF").oninput = lab; $("#vdN").oninput = lab; lab();
  $("#vdGo").onclick = ev => busy(ev.target, $("#vdMsg"), async () => vdShow(await api("/signals/video", { kind: $("#vdK").value, factor: +$("#vdF").value, noise: +$("#vdN").value })));
}, "video");
