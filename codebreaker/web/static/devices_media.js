/* Cameras and microphones, analysed in the browser: nothing leaves the page. Each has its own start and stop. */
const MEDIA = { cam: { stream: null, timer: null }, mic: { stream: null, timer: null, audio: null } };
const DTMF = { rows: [697, 770, 852, 941], cols: [1209, 1336, 1477, 1633], keys: ["123A", "456B", "789C", "*0#D"] };

function mediaHalt(kind) {
  const m = MEDIA[kind];
  if (m.timer) clearInterval(m.timer);
  if (m.stream) m.stream.getTracks().forEach(t => t.stop());
  if (m.audio) m.audio.close();
  m.stream = m.timer = null;
  if (kind === "mic") m.audio = null;
  const [go, stop] = kind === "cam" ? ["#mvGo", "#mvStop"] : ["#maGo", "#maStop"];
  if ($(go)) { $(go).disabled = false; $(stop).disabled = true; }
  if (kind === "cam" && $("#mvV")) $("#mvV").srcObject = null;
}

function mediaStop() { mediaHalt("cam"); mediaHalt("mic"); }

function mediaPanels() {
  return `<div class="two"><div class="panel"><h3>Camera</h3><p class="mute">Measures each frame: brightness, colour, motion and sharpness, and reads QR codes where the browser supports it.</p><select id="mvSel" aria-label="Camera"></select><button id="mvGo">Start camera</button><button id="mvStop" class="alt" disabled>Stop camera</button><video id="mvV" playsinline muted style="width:100%;max-height:260px;background:#000;margin-top:8px"></video><div id="mvOut"></div></div>
    <div class="panel"><h3>Microphone</h3><p class="mute">Shows the spectrum, the loudest frequency, and touch-tone (DTMF) keys if heard.</p><select id="maSel" aria-label="Microphone"></select><button id="maGo">Start microphone</button><button id="maStop" class="alt" disabled>Stop microphone</button><canvas id="maC" width="520" height="140" style="width:100%;background:#05040e;margin-top:8px"></canvas><div id="maOut"></div></div></div>`;
}

async function mediaList() {
  const ds = await navigator.mediaDevices.enumerateDevices();
  const fill = (sel, kind, label) => { $(sel).innerHTML = ds.filter(d => d.kind === kind).map((d, i) => `<option value="${esc(d.deviceId)}">${esc(d.label || `${label} ${i + 1}`)}</option>`).join(""); };
  fill("#mvSel", "videoinput", "Camera"); fill("#maSel", "audioinput", "Microphone");
}

function goertzel(data, rate, f) {
  const k = 2 * Math.cos(2 * Math.PI * f / rate);
  let s1 = 0, s2 = 0;
  for (const x of data) { const s = x + k * s1 - s2; s2 = s1; s1 = s; }
  return s1 * s1 + s2 * s2 - k * s1 * s2;
}

function dtmfKey(data, rate) {
  const r = DTMF.rows.map(f => goertzel(data, rate, f)), c = DTMF.cols.map(f => goertzel(data, rate, f));
  const ri = r.indexOf(Math.max(...r)), ci = c.indexOf(Math.max(...c));
  const others = [...r, ...c].sort((a, b) => b - a)[2] || 1;
  return r[ri] > 20 * others && c[ci] > 20 * others && r[ri] > 1 ? DTMF.keys[ri][ci] : "";
}

function camStats(ctx, w, h, prev) {
  const d = ctx.getImageData(0, 0, w, h).data, hist = new Array(32).fill(0);
  let r = 0, g = 0, b = 0, diff = 0, lap = 0;
  const gray = new Float32Array(w * h);
  for (let i = 0, p = 0; i < d.length; i += 4, p++) { r += d[i]; g += d[i + 1]; b += d[i + 2]; const y = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]; gray[p] = y; hist[Math.min(31, y >> 3)]++; if (prev) diff += Math.abs(y - prev[p]) > 25 ? 1 : 0; }
  for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) { const p = y * w + x, v = 4 * gray[p] - gray[p - 1] - gray[p + 1] - gray[p - w] - gray[p + w]; lap += v * v; }
  const n = w * h;
  return { gray, hist, mean: [r / n, g / n, b / n].map(Math.round), motion: prev ? diff / n : 0, sharp: lap / n };
}

function mediaSetup() {
  if (!navigator.mediaDevices) { $("#mvOut").innerHTML = '<p class="err">This browser does not allow camera or microphone access here.</p>'; return; }
  mediaList().catch(() => {});
  $("#mvStop").onclick = () => { mediaHalt("cam"); $("#mvOut").insertAdjacentHTML("afterbegin", '<p class="mute">Camera stopped.</p>'); };
  $("#maStop").onclick = () => { mediaHalt("mic"); $("#maOut").insertAdjacentHTML("afterbegin", '<p class="mute">Microphone stopped.</p>'); };
  $("#mvGo").onclick = async () => {
    mediaHalt("cam");
    $("#mvGo").disabled = true; $("#mvStop").disabled = false;
    const M = MEDIA.cam;
    try {
      M.stream = await navigator.mediaDevices.getUserMedia({ video: $("#mvSel").value ? { deviceId: { exact: $("#mvSel").value } } : true });
      await mediaList();
      const v = $("#mvV"); v.srcObject = M.stream; await v.play();
      const s = M.stream.getVideoTracks()[0].getSettings(), c = document.createElement("canvas"), w = 160, h = Math.round(160 * v.videoHeight / v.videoWidth);
      c.width = w; c.height = h;
      const ctx = c.getContext("2d", { willReadFrequently: true }), det = "BarcodeDetector" in window ? new BarcodeDetector({ formats: ["qr_code", "ean_13", "code_128"] }) : null;
      let prev = null, frames = 0, t0 = performance.now();
      const count = () => { frames++; if (M.stream) v.requestVideoFrameCallback(count); };
      if (v.requestVideoFrameCallback) v.requestVideoFrameCallback(count);
      M.timer = setInterval(async () => {
        ctx.drawImage(v, 0, 0, w, h);
        const st = camStats(ctx, w, h, prev); prev = st.gray;
        const fps = frames / ((performance.now() - t0) / 1000); frames = 0; t0 = performance.now();
        let codes = "";
        if (det) { try { codes = (await det.detect(v)).map(x => `${x.format}: ${x.rawValue}`).join("; "); } catch { codes = ""; } }
        const max = Math.max(...st.hist);
        $("#mvOut").innerHTML = `${table(["Resolution", "Frames/s", "Mean R, G, B", "Motion", "Sharpness"], [[`${s.width}×${s.height}`, fps.toFixed(1), st.mean.join(", "), `${(st.motion * 100).toFixed(1)}%`, Math.round(st.sharp)]])}<div class="cbars" role="img" aria-label="Brightness histogram">${st.hist.map((x, i) => `<i style="height:${Math.max(2, x / max * 100)}%" title="Brightness ${i * 8}-${i * 8 + 7}: ${x} pixels"></i>`).join("")}</div><p class="mute">Brightness histogram, dark to light.${det ? "" : " QR reading is not supported in this browser."}</p>${codes ? `<p><b>Code read:</b> ${esc(codes)}</p>` : ""}`;
      }, 500);
    } catch (e) { mediaHalt("cam"); $("#mvOut").innerHTML = `<p class="err">${esc(e.message)}. Allow camera access for this page in the browser.</p>`; }
  };
  $("#maGo").onclick = async () => {
    mediaHalt("mic");
    $("#maGo").disabled = true; $("#maStop").disabled = false;
    const M = MEDIA.mic;
    try {
      M.stream = await navigator.mediaDevices.getUserMedia({ audio: $("#maSel").value ? { deviceId: { exact: $("#maSel").value }, echoCancellation: false, noiseSuppression: false } : true });
      await mediaList();
      const ac = new AudioContext(); M.audio = ac; await ac.resume();
      const an = ac.createAnalyser(); an.fftSize = 4096; ac.createMediaStreamSource(M.stream).connect(an);
      const freq = new Float32Array(an.frequencyBinCount), wave = new Float32Array(an.fftSize), cv = $("#maC"), g = cv.getContext("2d");
      let keys = "";
      M.timer = setInterval(() => {
        an.getFloatFrequencyData(freq); an.getFloatTimeDomainData(wave);
        const rms = Math.sqrt(wave.reduce((a, x) => a + x * x, 0) / wave.length), db = 20 * Math.log10(rms || 1e-9);
        let peak = 1; for (let i = 2; i < freq.length; i++) if (freq[i] > freq[peak]) peak = i;
        const hz = peak * ac.sampleRate / an.fftSize, key = dtmfKey(wave, ac.sampleRate);
        if (key && keys.slice(-1) !== key) keys += key;
        g.fillStyle = "#05040e"; g.fillRect(0, 0, cv.width, cv.height); g.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--c1");
        const bins = 104;
        for (let b = 0; b < bins; b++) { const lo = Math.floor(Math.pow(freq.length, b / bins)), hi = Math.max(lo + 1, Math.floor(Math.pow(freq.length, (b + 1) / bins))); let m = -140; for (let i = lo; i < hi; i++) m = Math.max(m, freq[i]); const hgt = Math.max(1, (m + 120) / 100 * cv.height); g.fillRect(b * 5, cv.height - hgt, 4, hgt); }
        $("#maOut").innerHTML = `${table(["Level", "Loudest frequency", "Sample rate", "Touch-tone keys heard"], [[`${db.toFixed(1)} dBFS`, `${Math.round(hz)} Hz`, `${ac.sampleRate} Hz`, keys || "none"]])}<p class="mute">Spectrum from low to high frequency on a log scale.</p>`;
      }, 120);
    } catch (e) { mediaHalt("mic"); $("#maOut").innerHTML = `<p class="err">${esc(e.message)}. Allow microphone access for this page in the browser.</p>`; }
  };
}
