/* Puzzle section: an animated 3D Rubik's cube and a sudoku solver. */
const CUBE_COL = { U: "#f4f4f0", D: "#f5d800", F: "#17b45a", B: "#2b6cf0", R: "#e0263a", L: "#ff7a14" };
const SIZE = 56;

route(/^\/puzzles$/, async () => {
  view().innerHTML = `<p class="kicker">// PUZZLES</p><h1>Puzzles</h1><p class="lead">Solving a Rubik's cube and breaking a cipher are both searches through an enormous space, guided by structure.</p>
    <div class="grid"><a class="card" href="#/learn"><b>Learn to solve</b><span>Step-by-step guides for doing these yourself.</span></a><a class="card" href="#/puzzles/cube"><b>Rubik's cube</b><span>Scramble it, turn it, and watch a two-phase solver finish it.</span></a><a class="card" href="#/puzzles/sudoku"><b>Sudoku</b><span>Watch constraint search fill the grid.</span></a><a class="card" href="#/puzzles/scan-cube"><b>Scan a real cube</b><span>Show each face to the camera, or use photos, and get a solution.</span></a><a class="card" href="#/puzzles/scan-sudoku"><b>Scan a sudoku</b><span>Photograph a puzzle, correct any misreads, and solve it.</span></a><a class="card" href="#/puzzles/mastermind"><b>Mastermind</b><span>Codebreaking by deduction, with minimax guesses.</span></a><a class="card" href="#/puzzles/lights"><b>Lights Out</b><span>A puzzle solved by linear algebra.</span></a><a class="card" href="#/puzzles/sliding"><b>Sliding tiles</b><span>Shortest solutions by A* search.</span></a><a class="card" href="#/puzzles/hanoi"><b>Tower of Hanoi</b><span>Recursion you can watch.</span></a><a class="card" href="#/puzzles/queens"><b>N-Queens</b><span>Backtracking, the idea behind the bombe.</span></a><a class="card" href="#/puzzles/knight"><b>Knight's Tour</b><span>A simple rule that visits every square.</span></a><a class="card" href="#/puzzles/nonogram"><b>Nonogram</b><span>Pictures revealed by pure logic.</span></a><a class="card" href="#/math/groups"><b>The maths of permutations</b><span>Why the cube and Enigma are the same kind of object.</span></a></div>`;
}, "puzzles");

function matrixFor(pos, n, scale) {
  /* Column vectors: u, v, n and translation; screen y points down, so y is negated. */
  const axis = n.findIndex(v => v !== 0);
  const u = axis === 0 ? [0, 0, -n[0]] : [1, 0, 0];
  const v = axis === 1 ? [0, 0, n[1]] : [0, -1, 0];
  const t = [pos[0] * scale + n[0] * scale / 2, -(pos[1] * scale) - n[1] * scale / 2, pos[2] * scale + n[2] * scale / 2];
  return [u[0], -u[1], u[2], 0, v[0], -v[1], v[2], 0, n[0], -n[1], n[2], 0, t[0], t[1], t[2], 1];
}

route(/^\/puzzles\/cube$/, async () => {
  const faces = ["U", "D", "R", "L", "F", "B"];
  view().innerHTML = `<a href="#/puzzles">← Puzzles</a><h1>Rubik's cube</h1><p class="lead">The cube has 43,252,003,274,489,856,000 positions, yet every one can be solved in 20 moves or fewer. Drag the cube to look around it.</p>
    <div class="panel"><div class="scene" id="scene"><div class="cube" id="cube"></div></div>
    <div class="cubekeys">${faces.map(f => `<button type="button" data-m="${f}">${f}</button><button type="button" class="alt" data-m="${f}'">${f}'</button>`).join("")}</div>
    <div class="row"><div><label for="alg">Type your own moves</label><input id="alg" placeholder="For example, R U R' U'"></div></div><button id="runalg" class="alt">Run moves</button>
    <button id="scr">Scramble</button><button id="sol">Solve it</button><button id="rst" class="alt">Reset</button><p id="st" class="mute"></p><pre id="log"> </pre></div>
    <h2>How the solver works</h2><p>Herbert Kociemba's two-phase algorithm first reaches a much smaller subgroup of positions, then solves within it using only moves that stay in that subgroup. Like a good cipher attack, it replaces one impossible search with two manageable ones.</p>`;
  let cube = window.PENDING_CUBE ? cubeFromFacelets(window.PENDING_CUBE) : newCube(), els = [], busy = false, rx = -28, ry = -36;
  window.PENDING_CUBE = null;
  const root = $("#cube");
  const paint = (angle = null, m = null) => {
    root.style.transform = `rotateX(${rx}deg) rotateY(${ry}deg)`;
    let axis, layer, dir;
    if (m) [axis, layer, dir] = AXES[m];
    cube.forEach((s, i) => {
      const base = `matrix3d(${matrixFor(s.pos, s.n, SIZE).join(",")})`;
      if (m && s.pos[axis] === layer) {
        const v = ["1,0,0", "0,-1,0", "0,0,1"][axis];
        els[i].style.transform = `rotate3d(${v},${angle * dir}deg) ${base}`;
      } else els[i].style.transform = base;
    });
  };
  root.innerHTML = cube.map(s => `<div class="sticker" style="background:${CUBE_COL[s.color]}"></div>`).join("");
  els = [...root.children];
  const status = () => { const f = facelets(cube); $("#st").textContent = f === SOLVED_CUBE ? "Solved." : "Scrambled."; };
  const animate = m => new Promise(done => {
    const { face, turns } = parseMove(m), total = turns === 2 ? 180 : 90, sign = turns === 3 ? -1 : 1, dur = matchMedia("(prefers-reduced-motion: reduce)").matches ? 1 : turns === 2 ? 330 : 220, t0 = performance.now();
    const frame = now => {
      if (!location.hash.startsWith("#/puzzles/cube")) return done();
      const p = Math.min(1, (now - t0) / dur);
      paint(sign * total * p, face);
      if (p < 1) requestAnimationFrame(frame); else { applyMove(cube, m); paint(); done(); }
    };
    requestAnimationFrame(frame);
  });
  const run = async moves => { if (busy) return; busy = true; for (const m of moves) await animate(m); busy = false; status(); };
  document.querySelectorAll("[data-m]").forEach(b => { b.onclick = () => run([b.dataset.m]); });
  $("#scr").onclick = () => { const moves = []; let last = ""; while (moves.length < 22) { const m = CUBE_MOVES[Math.floor(Math.random() * 18)]; if (m[0] !== last) { moves.push(m); last = m[0]; } } $("#log").textContent = "Scramble: " + moves.join(" "); run(moves); };
  $("#sol").onclick = async () => {
    if (busy) return;
    try { const r = await api("/cube/solve", { facelets: facelets(cube) }); $("#log").textContent = r.moves.length ? `Solution in ${r.moves.length} moves: ${r.moves.join(" ")}` : "Already solved."; await run(r.moves); }
    catch (e) { $("#st").textContent = e.message; }
  };
  $("#runalg").onclick = () => { const m = $("#alg").value.trim().split(/\s+/).filter(Boolean); if (m.every(x => CUBE_MOVES.includes(x))) run(m); else $("#st").textContent = "Use moves such as R, U', or F2, separated by spaces."; };
  if (window.PENDING_ALG) { $("#alg").value = window.PENDING_ALG; window.PENDING_ALG = null; }
  $("#rst").onclick = () => { if (busy) return; cube = newCube(); paint(); status(); $("#log").textContent = " "; };
  let drag = null;
  $("#scene").onpointerdown = e => { drag = [e.clientX, e.clientY, rx, ry]; e.target.setPointerCapture?.(e.pointerId); };
  $("#scene").onpointermove = e => { if (!drag) return; ry = drag[3] + (e.clientX - drag[0]) * 0.6; rx = Math.max(-85, Math.min(85, drag[2] - (e.clientY - drag[1]) * 0.6)); paint(); };
  $("#scene").onpointerup = () => { drag = null; };
  paint(); status();
}, "puzzles");

route(/^\/puzzles\/sudoku$/, async () => {
  const P = "530070000600195000098000060800060003400803001700020006060000280000419005000080079";
  view().innerHTML = `<a href="#/puzzles">← Puzzles</a><h1>Sudoku</h1><p class="lead">The solver always fills the cell with the fewest options, and backtracks when it hits a contradiction: the same logic as the bombe.</p>
    <div class="panel center"><div id="g" class="sudoku"></div><button id="go">Solve</button><button id="rs" class="alt">Reset</button><p id="n" class="mute"></p></div>`;
  let timer, cells;
  const start = () => [...P].map(Number);
  const draw = (g, hi = -1) => { $("#g").innerHTML = g.map((v, i) => `<div class="${P[i] !== "0" ? "given" : ""} ${i === hi ? "hi" : ""}">${v || ""}</div>`).join(""); };
  const reset = () => { clearInterval(timer); cells = start(); draw(cells); $("#n").textContent = ""; };
  $("#go").onclick = () => {
    clearInterval(timer); cells = start();
    const work = start(), tr = []; solveSudoku(work, tr);
    let i = 0;
    timer = setInterval(() => { if (!location.hash.endsWith("/sudoku")) return clearInterval(timer); const [c, v] = tr[i++]; cells[c] = v; draw(cells, c); $("#n").textContent = `${i} of ${tr.length} steps`; if (i >= tr.length) clearInterval(timer); }, 40);
  };
  $("#rs").onclick = reset; reset();
}, "puzzles");
