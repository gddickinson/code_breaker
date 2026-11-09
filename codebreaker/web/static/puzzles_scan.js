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
  view().innerHTML = `<a href="#/puzzles">← Puzzles</a><h1>Scan a real cube</h1><p class="lead">Show each face in turn, lined up with the grid. Pictures stay on this computer. Tap any sticker to correct it.</p>
    <div class="panel"><div class="scanbox"><video id="v" playsinline muted></video><div class="gridov"></div></div><p id="msg" class="err"></p><p id="st" class="reading"></p>
    <button id="cam">Start camera</button><button id="snap">Capture this face</button><label class="filebtn">Use a photo instead<input id="file" type="file" accept="image/*"></label></div>
    <div class="panel"><h3>What was read</h3><div id="net" class="net"></div><p id="n" class="mute"></p><button id="solve">Solve this cube</button><button id="clear" class="alt">Start again</button></div>`;
  const cam = camera($("#v"), $("#msg")); leaveOff(cam, "#/puzzles/scan-cube");
  let face = 0, samples = Array(54).fill(null), letters54 = null;
  const COLS = l => CUBE_COL[l];
  const note = () => { $("#st").textContent = face < 6 ? `Face ${face + 1} of 6. ${FACE_STEPS[face][2]}` : "All six faces read."; };
  const draw = () => {
    const pos = { U: [3, 0], L: [0, 3], F: [3, 3], R: [6, 3], B: [9, 3], D: [3, 6] };
    let h = "";
    "URFDLB".split("").forEach((f, fi) => { for (let i = 0; i < 9; i++) { const n = fi * 9 + i, s = samples[n], col = letters54 ? COLS(letters54[n]) : s ? `rgb(${s})` : "#1b1638"; h += `<button type="button" class="st" data-n="${n}" aria-label="Sticker ${n + 1}" style="grid-column:${pos[f][0] + (i % 3) + 1};grid-row:${pos[f][1] + Math.floor(i / 3) + 1};background:${col}"></button>`; } });
    $("#net").innerHTML = h;
    document.querySelectorAll(".st").forEach(b => { b.onclick = () => { if (!letters54) return; const n = +b.dataset.n; if (n % 9 === 4) return; const o = "URFDLB", arr = [...letters54]; arr[n] = o[(o.indexOf(arr[n]) + 1) % 6]; letters54 = arr.join(""); draw(); }; });
    if (letters54) { const c = {}; [...letters54].forEach(l => { c[l] = (c[l] || 0) + 1; }); $("#n").textContent = Object.values(c).every(v => v === 9) ? "Nine stickers of each colour." : "Each colour must appear exactly nine times. Tap stickers to correct them."; }
  };
  const take = canvas => {
    if (face >= 6) return;
    const g = canvas.getContext("2d", { willReadFrequently: true }), size = canvas.width, cell = size / 3;
    for (let i = 0; i < 9; i++) {
      const cx = (i % 3 + 0.5) * cell, cy = (Math.floor(i / 3) + 0.5) * cell, r = cell * 0.18, d = g.getImageData(cx - r, cy - r, 2 * r, 2 * r).data, ch = [[], [], []];
      for (let j = 0; j < d.length; j += 4) for (let k = 0; k < 3; k++) ch[k].push(d[j + k]);
      samples[face * 9 + i] = ch.map(v => v.sort((a, b) => a - b)[v.length >> 1]);
    }
    face++;
    if (face === 6) letters54 = classifyCube(samples);
    note(); draw();
  };
  $("#cam").onclick = () => cam.start();
  $("#snap").onclick = () => { if (!cam.on) { $("#msg").textContent = "Start the camera first, or use a photo."; return; } take(squareCanvas($("#v"), $("#v").videoWidth, $("#v").videoHeight, 300)); };
  $("#file").onchange = async e => { try { const i = await loadFile(e.target.files[0]); take(squareCanvas(i, i.naturalWidth, i.naturalHeight, 300)); e.target.value = ""; } catch (x) { $("#msg").textContent = x.message; } };
  $("#clear").onclick = () => { face = 0; samples = Array(54).fill(null); letters54 = null; $("#n").textContent = ""; note(); draw(); };
  $("#solve").onclick = async () => { if (!letters54) { $("#n").textContent = "Scan all six faces first."; return; } try { await api("/cube/solve", { facelets: letters54 }); window.PENDING_CUBE = letters54; location.hash = "#/puzzles/cube"; } catch { $("#n").textContent = "That is not a reachable cube position, so a sticker was probably misread. Correct it and try again."; } };
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
