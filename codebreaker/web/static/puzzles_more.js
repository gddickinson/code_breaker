/* More puzzle types, each with a solver you can watch. */
const pzBack = '<a href="#/puzzles">← Puzzles</a>';
const onPage = h => location.hash === h;

route(/^\/puzzles\/mastermind$/, async () => {
  const C = ["#e0263a", "#2b6cf0", "#17b45a", "#f5d800", "#b388ff", "#f4f4f0"], N = ["Red", "Blue", "Green", "Yellow", "Purple", "White"];
  const dot = v => `<i class="peg" style="background:${C[v]}" title="${N[v]}"></i>`;
  let secret = [0, 1, 2, 3];
  view().innerHTML = `${pzBack}<h1>Mastermind</h1><p class="lead">A codebreaking game. Pick a secret code and watch the computer deduce it from feedback alone, removing every code that no longer fits.</p>
    <div class="panel"><div class="row">${[0, 1, 2, 3].map(i => `<div><label for="p${i}">Peg ${i + 1}</label><select id="p${i}">${N.map((n, v) => `<option value="${v}" ${v === secret[i] ? "selected" : ""}>${n}</option>`).join("")}</select></div>`).join("")}</div><button id="go">Break this code</button><div id="o"></div></div>`;
  $("#go").onclick = () => { secret = [0, 1, 2, 3].map(i => +$("#p" + i).value); const log = mmSolve(secret); $("#o").innerHTML = `<div class="scroll"><table><thead><tr><th>Guess</th><th>Code</th><th>Right place</th><th>Right colour only</th><th>Codes remaining before this guess</th></tr></thead><tbody>${log.map((l, i) => `<tr><td>${i + 1}</td><td>${l.g.map(dot).join("")}</td><td>${Math.floor(l.f / 10)}</td><td>${l.f % 10}</td><td>${l.left}</td></tr>`).join("")}</tbody></table></div><p>Solved in ${log.length} guesses.</p>`; };
}, "puzzles");

route(/^\/puzzles\/lights$/, async () => {
  const n = 5; let g = Array(n * n).fill(0), shown = null;
  view().innerHTML = `${pzBack}<h1>Lights Out</h1><p class="lead">Each press toggles a light and its neighbours. It looks like trial and error, but it is linear algebra over two values: press order does not matter, and the solution comes from solving equations.</p>
    <div class="panel center"><div id="g" class="lights"></div><button id="new">New puzzle</button><button id="sol" class="alt">Show solution</button><p id="n" class="mute"></p></div><p><a href="#/math/linear">The maths of linear systems →</a></p>`;
  const draw = () => { $("#g").innerHTML = g.map((v, i) => `<button type="button" aria-label="Light ${i + 1}" data-i="${i}" class="lt ${v ? "on" : ""} ${shown && shown[i] ? "tip" : ""}"></button>`).join(""); document.querySelectorAll(".lt").forEach(b => { b.onclick = () => { g = lightsApply(g, n, +b.dataset.i); shown = null; draw(); if (g.every(v => !v)) $("#n").textContent = "All lights out."; }; }); };
  const fresh = () => { g = Array(n * n).fill(0); for (let i = 0; i < 14; i++) g = lightsApply(g, n, Math.floor(Math.random() * n * n)); shown = null; $("#n").textContent = ""; draw(); };
  $("#new").onclick = fresh; $("#sol").onclick = () => { shown = lightsOutSolve(g, n); $("#n").textContent = shown ? `Press the ${shown.filter(Boolean).length} marked lights.` : "This position cannot be solved."; draw(); }; fresh();
}, "puzzles");

route(/^\/puzzles\/sliding$/, async () => {
  let s = slidingScramble(Math.random), timer;
  view().innerHTML = `${pzBack}<h1>Sliding tiles</h1><p class="lead">Slide tiles into order. A* search finds a shortest solution, guided by how far each tile is from home.</p>
    <div class="panel center"><div id="g" class="tiles8"></div><button id="sc">Scramble</button><button id="so">Solve</button><p id="n" class="mute"></p></div>`;
  const draw = () => { $("#g").innerHTML = s.map((v, i) => `<button type="button" data-i="${i}" class="${v ? "" : "blank"}" ${v ? "" : "disabled"}>${v || ""}</button>`).join(""); document.querySelectorAll("#g button").forEach(b => { b.onclick = () => { const nb = slidingNeighbours(s).find(a => a[+b.dataset.i] === 0); if (nb) { s = nb; draw(); } }; }); };
  $("#sc").onclick = () => { clearInterval(timer); s = slidingScramble(Math.random); $("#n").textContent = ""; draw(); };
  $("#so").onclick = () => { clearInterval(timer); const p = slidingSolve(s); let i = 0; $("#n").textContent = `Shortest solution: ${p.length - 1} moves.`; timer = setInterval(() => { if (!onPage("#/puzzles/sliding") || i >= p.length) return clearInterval(timer); s = p[i++]; draw(); }, 260); };
  draw();
}, "puzzles");

route(/^\/puzzles\/hanoi$/, async () => {
  view().innerHTML = `${pzBack}<h1>Tower of Hanoi</h1><p class="lead">Move the stack one disc at a time, never placing a larger disc on a smaller one. The minimum is 2ⁿ − 1 moves.</p>
    <div class="panel"><label for="d">Discs: <b id="v"></b></label><input id="d" type="range" min="2" max="9" value="6"><button id="go">Solve</button><div id="g" class="hanoi"></div><p id="n" class="mute"></p></div>`;
  let peg, timer;
  const draw = () => { const k = +$("#d").value; $("#g").innerHTML = peg.map(p => `<div class="peg3">${[...p].reverse().map(d => `<span style="width:${18 + d * (72 / k)}%"></span>`).join("")}</div>`).join(""); };
  const reset = () => { clearInterval(timer); const k = +$("#d").value; $("#v").textContent = k; peg = [[...Array(k).keys()].map(i => k - i), [], []]; $("#n").textContent = `Minimum: ${2 ** k - 1} moves.`; draw(); };
  $("#d").oninput = reset; $("#go").onclick = () => { reset(); const m = hanoi(+$("#d").value); let i = 0; timer = setInterval(() => { if (!onPage("#/puzzles/hanoi") || i >= m.length) return clearInterval(timer); const [a, b] = m[i++]; peg[b].push(peg[a].pop()); draw(); $("#n").textContent = `Move ${i} of ${m.length}`; }, Math.max(35, 900 / m.length)); }; reset();
}, "puzzles");

function board(n, cell) { return `<div class="chess" style="grid-template-columns:repeat(${n},1fr)">${[...Array(n * n).keys()].map(i => `<div class="${(Math.floor(i / n) + i % n) % 2 ? "dk" : ""}">${cell(i)}</div>`).join("")}</div>`; }

route(/^\/puzzles\/queens$/, async () => {
  view().innerHTML = `${pzBack}<h1>N-Queens</h1><p class="lead">Place queens so that none attack each other. Backtracking search abandons a partial board at the first conflict.</p>
    <div class="panel center"><label for="k">Board size: <b id="v"></b></label><input id="k" type="range" min="4" max="14" value="8"><button id="go">Solve</button><div id="g"></div><p id="n" class="mute"></p></div>`;
  let timer;
  const show = (col, n) => { $("#g").innerHTML = board(n, i => (col[Math.floor(i / n)] === i % n ? "♛" : "")); };
  const reset = () => { clearInterval(timer); const n = +$("#k").value; $("#v").textContent = n; show(Array(n).fill(-1), n); $("#n").textContent = ""; };
  $("#k").oninput = reset; $("#go").onclick = () => { reset(); const n = +$("#k").value, r = nQueens(n), skip = Math.max(1, Math.ceil(r.trace.length / 400)); let i = 0; timer = setInterval(() => { if (!onPage("#/puzzles/queens")) return clearInterval(timer); if (i >= r.trace.length) { show(r.col, n); $("#n").textContent = `${r.trace.length.toLocaleString()} placements and retreats.`; return clearInterval(timer); } show(r.trace[i], n); i += skip; }, 30); }; reset();
}, "puzzles");

route(/^\/puzzles\/knight$/, async () => {
  view().innerHTML = `${pzBack}<h1>Knight's Tour</h1><p class="lead">Visit every square once with a chess knight. Warnsdorff's rule moves to the square with the fewest onward options. Select a starting square.</p><div class="panel center"><div id="g"></div><p id="n" class="mute"></p></div>`;
  const n = 8; let order = Array(64).fill(0), timer;
  const draw = () => { $("#g").innerHTML = board(n, i => `<button type="button" class="kn" data-i="${i}" aria-label="Square ${i + 1}">${order[i] || ""}</button>`); document.querySelectorAll(".kn").forEach(b => { b.onclick = () => run(+b.dataset.i); }); };
  const run = i => { clearInterval(timer); order = Array(64).fill(0); const p = knightsTour(n, i % n, Math.floor(i / n)); let k = 0; timer = setInterval(() => { if (!onPage("#/puzzles/knight") || k >= p.length) { $("#n").textContent = `${p.length} of 64 squares visited.`; return clearInterval(timer); } order[p[k][1] * n + p[k][0]] = k + 1; k++; draw(); }, 70); };
  draw();
}, "puzzles");

route(/^\/puzzles\/nonogram$/, async () => {
  const pics = { Heart: ["0110110", "1111111", "1111111", "1111111", "0111110", "0011100", "0001000"], Key: ["0111000", "1000100", "1000100", "0111000", "0010000", "0011100", "0011000"], Space: ["0010100", "0111110", "1101011", "1111111", "1011101", "1010101", "0001000"] };
  view().innerHTML = `${pzBack}<h1>Nonogram</h1><p class="lead">Number clues say how many filled cells run in each row and column. The solver keeps only what every possible fit of a line agrees on, then repeats.</p><div class="panel center"><label for="p">Picture</label><select id="p">${Object.keys(pics).map(k => `<option>${k}</option>`).join("")}</select><button id="go">Solve step by step</button><div id="g"></div><p id="n" class="mute"></p></div>`;
  let timer;
  const setup = () => { const pic = pics[$("#p").value].map(r => [...r].map(Number)); return { rows: pic.map(nonogramClues), cols: pic[0].map((_, x) => nonogramClues(pic.map(r => r[x]))) }; };
  const draw = (grid, c) => { const col = c.cols.map(a => `<th>${a.join("<br>")}</th>`).join(""); $("#g").innerHTML = `<table class="nono"><thead><tr><th></th>${col}</tr></thead><tbody>${grid.map((r, y) => `<tr><th>${c.rows[y].join(" ")}</th>${r.map(v => `<td class="${v === 1 ? "on" : v === 0 ? "off" : ""}">${v === 0 ? "·" : ""}</td>`).join("")}</tr>`).join("")}</tbody></table>`; };
  const reset = () => { clearInterval(timer); const c = setup(); draw(c.rows.map(() => Array(c.cols.length).fill(-1)), c); $("#n").textContent = ""; };
  $("#p").onchange = reset; $("#go").onclick = () => { reset(); const c = setup(), r = nonogramSolve(c.rows, c.cols); let i = 0; timer = setInterval(() => { if (!onPage("#/puzzles/nonogram") || i >= r.steps.length) { $("#n").textContent = r.complete ? "Solved by logic alone." : "Logic alone could not finish this one."; return clearInterval(timer); } draw(r.steps[i++], c); }, 500); }; reset();
}, "puzzles");
