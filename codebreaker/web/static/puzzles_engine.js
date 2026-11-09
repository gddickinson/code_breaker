/* Pure solvers for the extra puzzles, with no DOM use so they can be tested under node. */
function lightsOutSolve(grid, n) {
  const N = n * n, rows = [];
  for (let i = 0; i < N; i++) {
    const r = Array(N + 1).fill(0), y = Math.floor(i / n), x = i % n;
    [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]].forEach(([dx, dy]) => { const a = x + dx, b = y + dy; if (a >= 0 && a < n && b >= 0 && b < n) r[b * n + a] = 1; });
    r[N] = grid[i]; rows.push(r);
  }
  let piv = 0; const lead = [];
  for (let c = 0; c < N && piv < N; c++) {
    const s = rows.findIndex((r, i) => i >= piv && r[c]);
    if (s < 0) continue;
    [rows[piv], rows[s]] = [rows[s], rows[piv]];
    rows.forEach((r, i) => { if (i !== piv && r[c]) rows[i] = r.map((v, k) => v ^ rows[piv][k]); });
    lead.push(c); piv++;
  }
  if (rows.some((r, i) => i >= piv && r[N])) return null;
  const x = Array(N).fill(0);
  lead.forEach((c, i) => { x[c] = rows[i][N]; });
  return x;
}
function lightsApply(grid, n, i) { const o = [...grid], y = Math.floor(i / n), x = i % n; [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]].forEach(([dx, dy]) => { const a = x + dx, b = y + dy; if (a >= 0 && a < n && b >= 0 && b < n) o[b * n + a] ^= 1; }); return o; }

function slidingNeighbours(s) { const z = s.indexOf(0), out = []; [[-3, z > 2], [3, z < 6], [-1, z % 3 > 0], [1, z % 3 < 2]].forEach(([d, ok]) => { if (ok) { const a = [...s]; [a[z], a[z + d]] = [a[z + d], a[z]]; out.push(a); } }); return out; }
function slidingSolve(start) {
  const goal = "123456780", h = s => s.reduce((a, v, i) => a + (v ? Math.abs(Math.floor((v - 1) / 3) - Math.floor(i / 3)) + Math.abs(((v - 1) % 3) - (i % 3)) : 0), 0);
  const key = s => s.join(""), open = new Map(), g = new Map([[key(start), 0]]), parent = new Map();
  const buckets = []; const push = (s, f) => { (buckets[f] ||= []).push(s); };
  push(start, h(start));
  for (let f = 0; f < buckets.length; f++) {
    while (buckets[f] && buckets[f].length) {
      const s = buckets[f].pop(), k = key(s);
      if (k === goal) { const path = [s]; let c = k; while (parent.has(c)) { c = parent.get(c); path.unshift([...c].map(Number)); } return path; }
      if (h(s) + g.get(k) !== f) continue;
      for (const nb of slidingNeighbours(s)) { const nk = key(nb), d = g.get(k) + 1; if (!g.has(nk) || d < g.get(nk)) { g.set(nk, d); parent.set(nk, k); push(nb, d + h(nb)); } }
    }
  }
  return null;
}
function slidingScramble(r, steps = 60) { let s = [1, 2, 3, 4, 5, 6, 7, 8, 0]; for (let i = 0; i < steps; i++) { const nb = slidingNeighbours(s); s = nb[Math.floor(r() * nb.length)]; } return s; }

function hanoi(n, a = 0, b = 2, c = 1, out = []) { if (n) { hanoi(n - 1, a, c, b, out); out.push([a, b]); hanoi(n - 1, c, b, a, out); } return out; }

function nQueens(n) {
  const trace = [], col = Array(n).fill(-1);
  const ok = (r, c) => { for (let i = 0; i < r; i++) if (col[i] === c || Math.abs(col[i] - c) === r - i) return false; return true; };
  const go = r => { if (r === n) return true; for (let c = 0; c < n; c++) { if (ok(r, c)) { col[r] = c; trace.push([...col]); if (go(r + 1)) return true; col[r] = -1; trace.push([...col]); } } return false; };
  return { found: go(0), col: [...col], trace };
}

function knightsTour(n, sx, sy) {
  const D = [[1, 2], [2, 1], [2, -1], [1, -2], [-1, -2], [-2, -1], [-2, 1], [-1, 2]], key = (x, y) => y * n + x;
  const inb = (x, y) => x >= 0 && y >= 0 && x < n && y < n, seen = new Set([key(sx, sy)]), path = [[sx, sy]];
  const degree = (x, y) => D.filter(([a, b]) => inb(x + a, y + b) && !seen.has(key(x + a, y + b))).length;
  let [x, y] = [sx, sy];
  while (path.length < n * n) {
    const opts = D.map(([a, b]) => [x + a, y + b]).filter(([a, b]) => inb(a, b) && !seen.has(key(a, b))).sort((p, q) => degree(p[0], p[1]) - degree(q[0], q[1]) || (Math.abs(p[0] - n / 2) + Math.abs(p[1] - n / 2)) - (Math.abs(q[0] - n / 2) + Math.abs(q[1] - n / 2)));
    if (!opts.length) break;
    [x, y] = opts[0]; seen.add(key(x, y)); path.push([x, y]);
  }
  return path;
}

/* Mastermind: 4 pegs, 6 colours. Keep codes consistent with feedback, and choose guesses by minimax. */
function mmFeedback(g, s) { let black = 0; const a = Array(6).fill(0), b = Array(6).fill(0); for (let i = 0; i < 4; i++) { if (g[i] === s[i]) black++; else { a[g[i]]++; b[s[i]]++; } } let white = 0; for (let i = 0; i < 6; i++) white += Math.min(a[i], b[i]); return black * 10 + white; }
function mmAll() { const o = []; for (let a = 0; a < 6; a++) for (let b = 0; b < 6; b++) for (let c = 0; c < 6; c++) for (let d = 0; d < 6; d++) o.push([a, b, c, d]); return o; }
function mmNext(cands) {
  if (cands.length === 1296) return [0, 0, 1, 1];
  let best = cands[0], score = Infinity;
  for (const g of cands.slice(0, 220)) { const m = new Map(); for (const c of cands) { const f = mmFeedback(g, c); m.set(f, (m.get(f) || 0) + 1); } const w = Math.max(...m.values()); if (w < score) { score = w; best = g; } }
  return best;
}
function mmSolve(secret) { let c = mmAll(); const log = []; for (let i = 0; i < 12; i++) { const g = mmNext(c), f = mmFeedback(g, secret); log.push({ g, f, left: c.length }); if (f === 40) break; c = c.filter(x => mmFeedback(g, x) === f); } return log; }

/* Nonogram: enumerate each line's fits, keep cells that agree, repeat, and backtrack if needed. */
function lineFits(clue, len) { const out = []; const go = (i, pos, line) => { if (i === clue.length) { out.push(line.concat(Array(len - line.length).fill(0))); return; } const need = clue.slice(i).reduce((a, b) => a + b, 0) + clue.length - i - 1; for (let p = pos; p + need <= len; p++) { const l = line.concat(Array(p - line.length).fill(0), Array(clue[i]).fill(1)); if (i + 1 < clue.length) l.push(0); go(i + 1, l.length, l); } }; go(0, 0, []); return out; }
function nonogramSolve(rows, cols) {
  const h = rows.length, w = cols.length, grid = Array.from({ length: h }, () => Array(w).fill(-1)), steps = [];
  const fitsR = rows.map(c => lineFits(c, w)), fitsC = cols.map(c => lineFits(c, h));
  const pass = () => { let changed = false; const line = (arr, get, set) => { const cur = get(); const ok = arr.filter(f => f.every((v, i) => cur[i] < 0 || cur[i] === v)); if (!ok.length) throw new Error("contradiction"); cur.forEach((v, i) => { if (v < 0) { const a = ok[0][i]; if (ok.every(f => f[i] === a)) { set(i, a); changed = true; } } }); }; for (let y = 0; y < h; y++) line(fitsR[y], () => grid[y], (i, v) => { grid[y][i] = v; }); for (let x = 0; x < w; x++) line(fitsC[x], () => grid.map(r => r[x]), (i, v) => { grid[i][x] = v; }); steps.push(grid.map(r => [...r])); return changed; };
  while (pass());
  return { grid, steps, complete: grid.every(r => r.every(v => v >= 0)) };
}
function nonogramClues(line) { const o = []; let run = 0; for (const v of line) { if (v) run++; else if (run) { o.push(run); run = 0; } } if (run) o.push(run); return o.length ? o : []; }

if (typeof module !== "undefined") module.exports = { lightsOutSolve, lightsApply, slidingSolve, slidingScramble, hanoi, nQueens, knightsTour, mmFeedback, mmSolve, nonogramSolve, nonogramClues };
