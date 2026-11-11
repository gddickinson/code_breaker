/* Scripts & Glyphs: scan a photo or camera picture for signs, show each sign's five suggestions, let the user choose. */
let wsStream = null, wsResult = null, wsChoice = [];

function wsStop() { if (wsStream) { wsStream.getTracks().forEach(t => t.stop()); wsStream = null; } }

function wsDraw(dataUrl) {
  const img = new Image();
  img.onload = () => {
    const c = $("#wsCanvas"), scale = Math.min(1, 900 / img.width);
    c.width = img.width * scale; c.height = img.height * scale;
    const g = c.getContext("2d");
    g.drawImage(img, 0, 0, c.width, c.height);
    g.lineWidth = 2; g.font = "12px ui-monospace, monospace";
    wsResult.signs.forEach((s, i) => {
      const [x, y, w, h] = s.box.map(v => v * scale);
      g.strokeStyle = s.confident ? "#00f0ff" : "#ff5c7a";
      g.strokeRect(x, y, w, h);
      g.fillStyle = g.strokeStyle; g.fillText(String(i + 1), x, Math.max(10, y - 3));
    });
  };
  img.src = dataUrl;
}

function wsList() {
  const rows = wsResult.signs.map((s, i) => `<tr><td>${i + 1}</td><td>${s.confident ? "" : '<span class="err">no confident match</span>'}</td><td>${s.candidates.map((c, j) =>
    `<button class="alt glyph wsPick${wsChoice[i] === j ? " on" : ""}" data-i="${i}" data-j="${j}" title="${esc(c.name)}${c.code ? " (" + esc(c.code) + ")" : ""}, ${esc(c.script)}: ${esc(c.values.join(", ") || "no sound value")}">${esc(c.sign)} <small>${(c.p * 100).toFixed(0)}%</small></button>`).join(" ")}</td></tr>`).join("");
  $("#wsList").innerHTML = wsResult.signs.length ? `<div class="scroll"><table><thead><tr><th>#</th><th></th><th>Suggestions, most likely first (click to choose)</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p class="mute">${esc(wsResult.note)} Boxes in red fall under the noise threshold (${(wsResult.threshold * 100).toFixed(0)}%). Script votes: ${esc(Object.entries(wsResult.scripts).map(([k, v]) => k + " " + v).join(", ") || "none")}.</p>
    <button id="wsUse">Read the chosen signs</button>` : "<p>No signs were found. Try a sharper picture with dark signs on a light background, or the reverse.</p>";
  document.querySelectorAll(".wsPick").forEach(b => b.onclick = () => { wsChoice[+b.dataset.i] = +b.dataset.j; wsList(); });
  const u = $("#wsUse");
  if (u) u.onclick = () => {
    $("#wrText").value = wsResult.signs.map((s, i) => s.candidates[wsChoice[i] ?? 0].sign).join("");
    $("#wrRead").click(); $("#wrText").scrollIntoView({ behavior: "smooth" });
  };
}

async function wsScan(dataUrl) {
  $("#wsMsg").textContent = "Scanning…";
  try {
    wsResult = await api("/writing/scan", { image: dataUrl, scripts: $("#wsScript").value ? [$("#wsScript").value] : [] });
    wsChoice = wsResult.signs.map(() => 0);
    $("#wsMsg").textContent = `${wsResult.signs.length} sign(s) found.`;
    wsDraw(dataUrl); wsList();
  } catch (e) { $("#wsMsg").innerHTML = `<span class="err">${esc(e.message)}</span>`; }
}

function wsPanel(scripts) {
  return `<h2>Scan a picture</h2><div class="panel"><p>Find signs in a photo or a scan and suggest what each one is. The recogniser learned from font drawings of every sign, so it is surest with clear printed or drawn signs; for worn carvings, pick from its five suggestions.</p>
    <div class="row"><div><label for="wsScript">Script</label><select id="wsScript"><option value="">Any script</option>${scripts.map(s => `<option value="${s.id}">${esc(s.title)}</option>`).join("")}</select></div></div>
    <label class="filebtn">Choose a picture<input id="wsFile" type="file" accept="image/*"></label> <button id="wsCam" class="alt">Start camera</button> <button id="wsSnap" class="alt" disabled>Scan the camera view</button>
    <div class="scanbox wide" id="wsBox" hidden><video id="wsVid" playsinline muted></video></div><p id="wsMsg" aria-live="polite"></p>
    <canvas id="wsCanvas" style="max-width:100%"></canvas><div id="wsList" aria-live="polite"></div></div>`;
}

function wsWire() {
  $("#wsFile").onchange = e => { const f = e.target.files[0]; if (!f) return; const r = new FileReader(); r.onload = () => wsScan(r.result); r.readAsDataURL(f); };
  $("#wsCam").onclick = async () => {
    if (wsStream) { wsStop(); $("#wsBox").hidden = true; $("#wsSnap").disabled = true; $("#wsCam").textContent = "Start camera"; return; }
    try { wsStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment", width: 1280 } }); $("#wsVid").srcObject = wsStream; await $("#wsVid").play(); $("#wsBox").hidden = false; $("#wsSnap").disabled = false; $("#wsCam").textContent = "Stop camera"; }
    catch (e) { $("#wsMsg").innerHTML = `<span class="err">The camera could not be opened: ${esc(e.message)}</span>`; }
  };
  $("#wsSnap").onclick = () => { const v = $("#wsVid"), c = document.createElement("canvas"); c.width = v.videoWidth; c.height = v.videoHeight; c.getContext("2d").drawImage(v, 0, 0); wsScan(c.toDataURL("image/jpeg", 0.9)); };
  window.addEventListener("hashchange", wsStop, { once: true });
}
