/* Read puzzles from a camera or photo. Images are processed on this computer only. */
function camera(videoEl, msgEl) {
  let stream = null;
  return {
    async start() {
      try { stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment", width: 1280 } }); videoEl.srcObject = stream; await videoEl.play(); msgEl.textContent = ""; return true; }
      catch { msgEl.textContent = "The camera could not be opened. Check browser permission, or use a photo instead."; return false; }
    },
    stop() { if (stream) stream.getTracks().forEach(t => t.stop()); stream = null; },
    get on() { return !!stream; },
  };
}
const leaveOff = (cam, hashStart) => { const f = () => { if (!location.hash.startsWith(hashStart)) { cam.stop(); removeEventListener("hashchange", f); } }; addEventListener("hashchange", f); };
function squareCanvas(source, w, h, size) {
  const c = document.createElement("canvas"); c.width = c.height = size;
  const s = Math.min(w, h); c.getContext("2d", { willReadFrequently: true }).drawImage(source, (w - s) / 2, (h - s) / 2, s, s, 0, 0, size, size);
  return c;
}
function loadFile(file) { return new Promise((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = () => no(new Error("That file could not be read as an image.")); i.src = URL.createObjectURL(file); }); }

const FACE_STEPS = [["U", "white", "Top face. Keep the front face towards the bottom of the picture."], ["R", "right", "Right face, with the top face upward."], ["F", "front", "Front face, with the top face upward."], ["D", "bottom", "Bottom face. Keep the front face towards the top of the picture."], ["L", "left", "Left face, with the top face upward."], ["B", "back", "Back face, with the top face upward."]];

route(/^\/puzzles\/scan-cube$/, async () => {
  view().innerHTML = `<a href="#/puzzles">← Puzzles</a><h1>Scan a real cube</h1><p class="lead">Click a side on the map, then photograph it. Drag sides to where they belong. Pictures stay on this computer.</p>
    <div class="scanlay"><div class="panel"><div class="scanbox"><video id="v" playsinline muted></video><div class="gridov"></div></div><p id="msg" class="err"></p><p id="st" class="reading" aria-live="polite"></p>
    <button id="cam">Start camera</button><button id="snap">Capture this side</button><label class="filebtn">Use a photo instead<input id="file" type="file" accept="image/*"></label></div>
    <div class="panel"><h3>Your cube</h3><div id="net" class="net"></div><p class="mute">Click a side to choose it. Drag a side onto another to swap them. Once all six are read, click a side&#39;s centre to choose it, or any other sticker to change its colour.</p><div class="row"><button id="rot" class="alt">Rotate chosen side ↻</button></div><p id="n" class="mute"></p><button id="solve">Solve this cube</button><button id="clear" class="alt">Start again</button></div></div>`;
  const cam = camera($("#v"), $("#msg")); leaveOff(cam, "#/puzzles/scan-cube");
  const NET = [[3, 0], [6, 3], [3, 3], [3, 6], [0, 3], [9, 3]], NAMES = ["Top", "Right", "Front", "Bottom", "Left", "Back"];
  let sel = 0, samples = Array(54).fill(null), cols = null, palette = {}, drag = null, justDragged = false;
  const faceRead = f => samples[f * 9] !== null;
  const reclassify = () => {
    if (!samples.every(Boolean)) { cols = null; return; }
    cols = [...classifyCube(samples)]; palette = {};
    for (const l of "URFDLB") { const m = samples.filter((_, i) => cols[i] === l); palette[l] = [0, 1, 2].map(k => Math.round(m.reduce((a, s) => a + s[k], 0) / m.length)); }
  };
  const colour = n => cols ? `rgb(${palette[cols[n]]})` : samples[n] ? `rgb(${samples[n]})` : "#1b1638";
  const note = () => { $("#st").textContent = sel < 0 ? "All six sides read. Click a side to photograph it again." : `Next photo: ${NAMES[sel]}. ${FACE_STEPS[sel][2]}`; };
  const draw = () => {
    let h = "";
    NET.forEach(([x, y], f) => {
      for (let i = 0; i < 9; i++) { const n = f * 9 + i; h += `<button type="button" class="st" data-n="${n}" aria-label="${NAMES[f]} side, sticker ${i + 1}" style="grid-column:${x + (i % 3) + 1};grid-row:${y + Math.floor(i / 3) + 1};background:${colour(n)}">${i === 4 ? `<span>${NAMES[f]}</span>` : ""}</button>`; }
      h += `<i class="netface${f === sel ? " sel" : ""}${drag && drag.over === f ? " over" : ""}" style="grid-column:${x + 1}/span 3;grid-row:${y + 1}/span 3"></i>`;
    });
    $("#net").innerHTML = h;
    if (cols) { const f = scanFacelets(cols); $("#n").textContent = f ? "Nine stickers of each colour." : "Each colour must appear nine times, with a different colour in the centre of every side."; }
    else $("#n").textContent = `${[0, 1, 2, 3, 4, 5].filter(faceRead).length} of 6 sides read.`;
  };
  const choose = f => { sel = f; note(); draw(); };
  const stickerAt = (x, y) => { const e = document.elementFromPoint(x, y), b = e && e.closest && e.closest(".st"); return b ? +b.dataset.n : null; };
  $("#net").onclick = e => {
    const b = e.target.closest(".st");
    if (!b || justDragged) { justDragged = false; return; }
    const n = +b.dataset.n, f = Math.floor(n / 9);
    if (cols && n % 9 !== 4) { const o = "URFDLB"; cols[n] = o[(o.indexOf(cols[n]) + 1) % 6]; draw(); return; }
    choose(f);
  };
  $("#net").onpointerdown = e => {
    const b = e.target.closest(".st");
    if (!b || e.button) return;
    const from = Math.floor(+b.dataset.n / 9), sx = e.clientX, sy = e.clientY;
    if (!faceRead(from)) return;
    let ghost = null;
    const move = m => {
      if (!ghost && Math.hypot(m.clientX - sx, m.clientY - sy) < 8) return;
      if (!ghost) {
        ghost = document.createElement("div"); ghost.className = "netghost";
        ghost.innerHTML = Array.from({ length: 9 }, (_, i) => `<b style="background:${colour(from * 9 + i)}"></b>`).join("");
        document.body.append(ghost); drag = { from, over: null };
      }
      ghost.style.left = `${m.clientX}px`; ghost.style.top = `${m.clientY}px`;
      const n = stickerAt(m.clientX, m.clientY), over = n === null ? null : Math.floor(n / 9);
      if (over !== drag.over) { drag.over = over; draw(); }
    };
    const up = u => {
      removeEventListener("pointermove", move); removeEventListener("pointerup", up); removeEventListener("pointercancel", up);
      if (!ghost) return;
      ghost.remove(); justDragged = true; setTimeout(() => { justDragged = false; }, 0);
      const n = u.type === "pointerup" ? stickerAt(u.clientX, u.clientY) : null, to = n === null ? from : Math.floor(n / 9);
      drag = null;
      if (to !== from) {
        samples = swapFaces(samples, from, to);
        if (cols) cols = swapFaces(cols, from, to);
        if (sel === from) sel = to; else if (sel === to) sel = from;
        note();
      }
      draw();
    };
    addEventListener("pointermove", move); addEventListener("pointerup", up); addEventListener("pointercancel", up);
  };
  $("#rot").onclick = () => {
    if (sel < 0 || !faceRead(sel)) { $("#n").textContent = "Choose a side that has been read."; return; }
    samples = rotateFace(samples, sel);
    if (cols) cols = rotateFace(cols, sel);
    draw();
  };
  const take = canvas => {
    if (sel < 0) { $("#msg").textContent = "Click the side you want to photograph."; return; }
    $("#msg").textContent = "";
    const g = canvas.getContext("2d", { willReadFrequently: true }), size = canvas.width, cell = size / 3;
    for (let i = 0; i < 9; i++) {
      const cx = (i % 3 + 0.5) * cell, cy = (Math.floor(i / 3) + 0.5) * cell, r = cell * 0.18, d = g.getImageData(cx - r, cy - r, 2 * r, 2 * r).data, ch = [[], [], []];
      for (let j = 0; j < d.length; j += 4) for (let k = 0; k < 3; k++) ch[k].push(d[j + k]);
      samples[sel * 9 + i] = ch.map(v => v.sort((a, b) => a - b)[v.length >> 1]);
    }
    const next = [1, 2, 3, 4, 5].map(k => (sel + k) % 6).find(f => !faceRead(f));
    sel = next === undefined ? -1 : next;
    reclassify(); note(); draw();
  };
  $("#cam").onclick = () => cam.start();
  $("#snap").onclick = () => { if (!cam.on) { $("#msg").textContent = "Start the camera first, or use a photo."; return; } take(squareCanvas($("#v"), $("#v").videoWidth, $("#v").videoHeight, 300)); };
  $("#file").onchange = async e => { try { const i = await loadFile(e.target.files[0]); take(squareCanvas(i, i.naturalWidth, i.naturalHeight, 300)); e.target.value = ""; } catch (x) { $("#msg").textContent = x.message; } };
  $("#clear").onclick = () => { sel = 0; samples = Array(54).fill(null); cols = null; note(); draw(); };
  $("#solve").onclick = async () => {
    const f = cols && scanFacelets(cols);
    if (!cols) { $("#n").textContent = "Scan all six sides first."; return; }
    if (!f) { $("#n").textContent = "Each colour must appear nine times, with a different colour in the centre of every side."; return; }
    try { await api("/cube/solve", { facelets: f }); window.PENDING_CUBE = f; location.hash = "#/puzzles/cube"; } catch { $("#n").textContent = "That is not a reachable cube position. Check that each side is in the right place and turned the right way."; }
  };
  note(); draw();
}, "puzzles");

route(/^\/puzzles\/scan-sudoku$/, async () => {
  view().innerHTML = `<a href="#/puzzles">← Puzzles</a><h1>Scan a sudoku</h1><p class="lead">Frame the whole grid, then read it. Check the digits, because a single misread makes a puzzle unsolvable.</p>
    <div class="panel"><div class="scanbox wide"><video id="v" playsinline muted></video></div><p id="msg" class="err"></p><button id="cam">Start camera</button><button id="snap">Read from camera</button><label class="filebtn">Use a photo<input id="file" type="file" accept="image/*"></label></div>
    <div class="panel center"><div id="g" class="sudoku edit"></div><button id="solve">Solve</button><button id="clr" class="alt">Clear</button><p id="n" class="mute"></p></div>`;
  const cam = camera($("#v"), $("#msg")); leaveOff(cam, "#/puzzles/scan-sudoku");
  let grid = Array(81).fill(0), given = Array(81).fill(false);
  const draw = () => { $("#g").innerHTML = grid.map((v, i) => `<input aria-label="Cell ${i + 1}" inputmode="numeric" maxlength="1" data-i="${i}" class="${given[i] ? "given" : ""}" value="${v || ""}">`).join(""); document.querySelectorAll(".edit input").forEach(e => { e.oninput = () => { const d = e.value.replace(/[^1-9]/g, "").slice(0, 1); e.value = d; grid[+e.dataset.i] = +d || 0; given[+e.dataset.i] = !!d; }; }); };
  const read = async dataUrl => { $("#n").textContent = "Reading the grid…"; try { const r = await api("/sudoku/read", { image: dataUrl }); grid = r.grid; given = grid.map(Boolean); draw(); $("#n").textContent = `${grid.filter(Boolean).length} digits read. Check them against the puzzle.`; } catch (e) { $("#n").textContent = e.message; } };
  $("#cam").onclick = () => cam.start();
  $("#snap").onclick = () => { if (!cam.on) { $("#msg").textContent = "Start the camera first, or use a photo."; return; } const v = $("#v"), c = document.createElement("canvas"); c.width = v.videoWidth; c.height = v.videoHeight; c.getContext("2d").drawImage(v, 0, 0); read(c.toDataURL("image/jpeg", 0.92)); };
  $("#file").onchange = e => { const f = e.target.files[0]; if (!f) return; const r = new FileReader(); r.onload = () => read(r.result); r.readAsDataURL(f); };
  $("#clr").onclick = () => { grid = Array(81).fill(0); given = Array(81).fill(false); draw(); $("#n").textContent = ""; };
  $("#solve").onclick = () => {
    const conflict = grid.some((v, i) => v && grid.some((w, j) => j !== i && w === v && (Math.floor(i / 9) === Math.floor(j / 9) || i % 9 === j % 9 || (Math.floor(i / 27) === Math.floor(j / 27) && Math.floor((i % 9) / 3) === Math.floor((j % 9) / 3)))));
    const work = [...grid];
    if (conflict || !solveSudoku(work)) { $("#n").textContent = "No solution exists from these digits, so one is probably misread. Correct it and try again."; return; }
    grid = work; draw(); $("#n").textContent = "Solved.";
  };
  draw();
}, "puzzles");
