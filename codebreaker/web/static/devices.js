/* Live Devices: find attached hardware, stream serial and network data, and analyse what arrives. */
const DV = { serial: null, net: null, ctl: [], sims: { "sim://gps": "Simulated GPS receiver", "sim://sensor": "Simulated sensor board", "sim://packets": "Simulated binary telemetry" } };

function dvStop() { ["serial", "net"].forEach(k => { if (DV[k]) DV[k].abort(); DV[k] = null; }); if (typeof mediaStop === "function") mediaStop(); }

async function dvStream(path, body, onEvent, slot) {
  const ctl = new AbortController();
  DV[slot] = ctl;
  const res = await fetch("/api" + path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: ctl.signal } : { signal: ctl.signal });
  if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || `Request failed (${res.status})`); }
  const reader = res.body.getReader(), dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop();
    lines.forEach(l => { if (l.trim()) onEvent(JSON.parse(l)); });
  }
}

function dvAnalysis(a) {
  const formats = Object.entries(a.formats);
  return `${table(["Bytes", "Kind", "Entropy (bits/byte)", "Printable", "Lines"], [[a.bytes, a.kind, a.entropy, `${Math.round(a.printable * 100)}%`, a.lines]])}
    ${formats.length ? formats.map(([k, v]) => `<h4>Recognised: ${esc(k)}</h4><pre>${esc(JSON.stringify(v, null, 1))}</pre>`).join("") : '<p class="mute">No known format recognised yet.</p>'}
    <p class="mute">Commonest bytes: ${a.top_bytes.map(([b, n]) => `${b} (${n})`).join(", ")}${Object.keys(a.line_endings).length ? `. Line endings: ${Object.entries(a.line_endings).map(([k, v]) => `${k} ${v}`).join(", ")}` : ""}.</p>`;
}

function dvRow(d) {
  const det = Object.entries(d.details).filter(([, v]) => v !== "" && v !== null).map(([k, v]) => `${esc(k)}: ${esc(String(v))}`).join(" · ");
  return `<tr><td>${esc(d.name)}</td><td class="mute">${det}${d.note ? `<br><span>${esc(d.note)}</span>` : ""}</td></tr>`;
}

function dvInventory(data) {
  const cats = [...new Set(data.devices.map(d => d.category))];
  const net = d => d.category !== "Network" || d.details.Address || d.details["Speed (Mb/s)"];
  return cats.map(c => { const all = data.devices.filter(d => d.category === c), shown = all.filter(net), hidden = all.length - shown.length;
    return `<details class="panel" ${["USB", "Camera", "Serial port"].includes(c) ? "open" : ""}><summary><b>${esc(c)}</b> <span class="mute">${all.length}</span></summary><div class="scroll"><table><tbody>${shown.map(dvRow).join("")}</tbody></table></div>${hidden ? `<p class="mute">${hidden} inactive interfaces hidden.</p>` : ""}</details>`; }).join("");
}

function dvSerialPanel(data) {
  const ports = data.devices.filter(d => d.category === "Serial port");
  return `<div class="panel"><h3>Serial port monitor</h3><p class="mute">Reads only: nothing is sent to the device. Simulated devices are included so the analysis can be tried without hardware.</p>
    <div class="row"><div><label for="dvP">Port</label><select id="dvP">${ports.map(p => `<option value="${esc(p.id)}">${esc(p.name)}</option>`).join("")}${Object.entries(DV.sims).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("")}</select></div>
    <div><label for="dvB">Baud rate</label><select id="dvB">${[1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600].map(b => `<option ${b === 9600 ? "selected" : ""}>${b}</option>`).join("")}</select></div></div>
    <button id="dvGo">Start monitoring</button><button id="dvHalt" class="alt" disabled>Stop</button><p id="dvNote" class="mute"></p><p id="dvMsg" aria-live="polite"></p>
    <div class="two"><div><h4>Latest bytes (hex)</h4><pre id="dvHex" class="mono"></pre></div><div><h4>As text</h4><pre id="dvTxt"></pre></div></div><div id="dvAn"></div></div>`;
}

function dvSerialSetup(data) {
  const notes = Object.fromEntries(data.devices.filter(d => d.category === "Serial port").map(d => [d.id, d.note]));
  const note = () => { $("#dvNote").textContent = notes[$("#dvP").value] || "Generated data, no hardware involved."; };
  $("#dvP").onchange = note; note();
  $("#dvGo").onclick = async () => {
    $("#dvGo").disabled = true; $("#dvHalt").disabled = false; $("#dvMsg").textContent = "Opening the port…";
    try {
      await dvStream("/devices/serial", { port: $("#dvP").value, baud: +$("#dvB").value, seconds: 300 }, e => {
        if (e.event === "data") { $("#dvMsg").textContent = `${e.total.toLocaleString()} bytes in ${e.elapsed} s (${e.rate} bytes/s).`; $("#dvHex").textContent = e.hex; $("#dvTxt").textContent = e.text.slice(-500); $("#dvAn").innerHTML = e.total ? dvAnalysis(e.analysis) : '<p class="mute">No data yet. Check the baud rate, or whether the device is sending.</p>'; }
        else if (e.event === "error") $("#dvMsg").innerHTML = `<span class="err">${esc(e.message)}</span>`;
        else if (e.event === "end") $("#dvMsg").textContent += " Finished.";
      }, "serial");
    } catch (x) { if (x.name !== "AbortError") $("#dvMsg").innerHTML = `<span class="err">${esc(x.message)}</span>`; }
    finally { $("#dvGo").disabled = false; $("#dvHalt").disabled = true; }
  };
  $("#dvHalt").onclick = () => { if (DV.serial) DV.serial.abort(); DV.serial = null; $("#dvMsg").textContent += " Stopped."; };
}

function dvNetSetup() {
  $("#nvStop").onclick = () => { if (DV.net) DV.net.abort(); DV.net = null; $("#nvOut").insertAdjacentHTML("afterbegin", '<p class="mute">Stopped.</p>'); };
  $("#nvGo").onclick = async () => {
    $("#nvGo").disabled = true; $("#nvStop").disabled = false;
    const fmt = v => v > 1e6 ? `${(v / 1e6).toFixed(2)} MB/s` : v > 1e3 ? `${(v / 1e3).toFixed(1)} kB/s` : `${v} B/s`;
    try {
      await dvStream("/devices/network?seconds=120", null, e => {
        if (e.event !== "rates") return;
        const max = Math.max(1, ...e.interfaces.map(r => r.in + r.out));
        $("#nvOut").innerHTML = `<p class="mute">Updated at ${e.elapsed} s. Counts come from the system, so no packets are captured or read.</p><div class="scroll"><table><thead><tr><th>Interface</th><th>In</th><th>Out</th><th>Packets in/out per s</th><th>Errors</th><th></th></tr></thead><tbody>${e.interfaces.map(r => `<tr><td>${esc(r.name)}</td><td>${fmt(r.in)}</td><td>${fmt(r.out)}</td><td>${r.packets_in} / ${r.packets_out}</td><td>${r.errors + r.drops}</td><td style="width:30%"><div style="height:10px;width:${(r.in + r.out) / max * 100}%;background:var(--c1);border-radius:0 3px 3px 0"></div></td></tr>`).join("")}</tbody></table></div>`;
      }, "net");
    } catch (x) { if (x.name !== "AbortError") $("#nvOut").innerHTML = `<p class="err">${esc(x.message)}</p>`; }
    finally { $("#nvGo").disabled = false; $("#nvStop").disabled = true; }
  };
}

route(/^\/devices$/, async () => {
  view().innerHTML = `<p class="kicker">// LIVE DEVICES</p><h1>Live devices</h1><p class="lead">What is attached to this computer, and what its data looks like as it arrives. Everything is read-only and stays on this machine.</p><p id="dvLoad" class="mute">Looking for devices…</p><div id="dvBody"></div>`;
  const leave = () => { if (!location.hash.startsWith("#/devices")) { dvStop(); removeEventListener("hashchange", leave); } };
  addEventListener("hashchange", leave);
  const load = async refresh => {
    const data = await api(`/devices${refresh ? "?refresh=true" : ""}`);
    $("#dvLoad").innerHTML = `${data.devices.length} devices found at ${esc(data.at)}. <button id="dvRe" class="alt">Look again</button>${data.kinect ? " A Kinect is attached; libfreenect support is planned." : ""}${data.errors.length ? ` <span class="err">Some checks failed: ${esc(data.errors.join("; "))}</span>` : ""}`;
    $("#dvBody").innerHTML = `${dvSerialPanel(data)}${mediaPanels()}<div class="panel"><h3>Network traffic</h3><p class="mute">Live throughput per interface.</p><button id="nvGo">Start</button><button id="nvStop" class="alt" disabled>Stop</button><div id="nvOut"></div></div><h2>Everything attached</h2>${dvInventory(data)}`;
    dvSerialSetup(data); mediaSetup(); dvNetSetup();
    $("#dvRe").onclick = () => { dvStop(); load(true); };
  };
  try { await load(false); } catch (e) { $("#dvLoad").innerHTML = `<span class="err">${esc(e.message)}</span>`; }
}, "devices");
