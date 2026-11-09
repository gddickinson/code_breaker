/* Rubik's cube model: stickers in 3D, and facelet strings for the Kociemba solver. No DOM use. */
const AXES = { U: [1, 1, -1], D: [1, -1, 1], R: [0, 1, -1], L: [0, -1, 1], F: [2, 1, -1], B: [2, -1, 1] };
const FACES = { U: [0, 1, 0], R: [1, 0, 0], F: [0, 0, 1], D: [0, -1, 0], L: [-1, 0, 0], B: [0, 0, -1] };

function newCube() {
  const stickers = [];
  for (const [f, n] of Object.entries(FACES)) {
    const axis = n.findIndex(v => v !== 0), others = [0, 1, 2].filter(i => i !== axis);
    for (const a of [-1, 0, 1]) for (const b of [-1, 0, 1]) {
      const pos = [0, 0, 0]; pos[axis] = n[axis]; pos[others[0]] = a; pos[others[1]] = b;
      stickers.push({ color: f, pos, n: [...n] });
    }
  }
  return stickers;
}

/* Rotate a vector by a signed quarter turn (+1 or -1) about axis 0, 1 or 2. */
function quarter(v, axis, s) {
  const [x, y, z] = v;
  if (axis === 0) return s > 0 ? [x, -z, y] : [x, z, -y];
  if (axis === 1) return s > 0 ? [z, y, -x] : [-z, y, x];
  return s > 0 ? [-y, x, z] : [y, -x, z];
}

function parseMove(m) { return { face: m[0], turns: m[1] === "2" ? 2 : m[1] === "'" ? 3 : 1 }; }

function applyMove(stickers, m) {
  const { face, turns } = parseMove(m), [axis, layer, dir] = AXES[face];
  for (let t = 0; t < turns; t++) for (const s of stickers) if (s.pos[axis] === layer) { s.pos = quarter(s.pos, axis, dir); s.n = quarter(s.n, axis, dir); }
}

/* Facelets in URFDLB order, each face read row by row as the solver expects. */
function faceletIndex(pos, n) {
  const [x, y, z] = pos;
  if (n[1] === 1) return 0 + (z + 1) * 3 + (x + 1);
  if (n[0] === 1) return 9 + (1 - y) * 3 + (1 - z);
  if (n[2] === 1) return 18 + (1 - y) * 3 + (x + 1);
  if (n[1] === -1) return 27 + (1 - z) * 3 + (x + 1);
  if (n[0] === -1) return 36 + (1 - y) * 3 + (z + 1);
  return 45 + (1 - y) * 3 + (1 - x);
}

function facelets(stickers) {
  const out = Array(54);
  for (const s of stickers) out[faceletIndex(s.pos, s.n)] = s.color;
  return out.join("");
}

const SOLVED_CUBE = "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB";
const CUBE_MOVES = ["U", "U'", "U2", "D", "D'", "D2", "R", "R'", "R2", "L", "L'", "L2", "F", "F'", "F2", "B", "B'", "B2"];

/* Sudoku: most-constrained-cell backtracking, recording each placement for animation. */
function solveSudoku(grid, trace = []) {
  const cands = i => { const used = new Set(); for (let k = 0; k < 9; k++) { used.add(grid[Math.floor(i / 9) * 9 + k]); used.add(grid[(i % 9) + k * 9]); used.add(grid[Math.floor(Math.floor(i / 9) / 3) * 27 + Math.floor((i % 9) / 3) * 3 + Math.floor(k / 3) * 9 + (k % 3)]); } return [1, 2, 3, 4, 5, 6, 7, 8, 9].filter(v => !used.has(v)); };
  let best = -1, bc = null;
  for (let i = 0; i < 81; i++) if (!grid[i]) { const c = cands(i); if (!bc || c.length < bc.length) { best = i; bc = c; if (c.length <= 1) break; } }
  if (best < 0) return true;
  for (const v of bc) { grid[best] = v; trace.push([best, v]); if (solveSudoku(grid, trace)) return true; grid[best] = 0; trace.push([best, 0]); }
  return false;
}

/* Load a facelet string into the sticker model, for a cube read from a photo. */
function cubeFromFacelets(str) {
  const c = newCube();
  for (const s of c) s.color = str[faceletIndex(s.pos, s.n)];
  return c;
}

function rgbToLab([r, g, b]) {
  const f = v => { v /= 255; return v > 0.04045 ? ((v + 0.055) / 1.055) ** 2.4 : v / 12.92; };
  const [R, G, B] = [f(r), f(g), f(b)];
  const h = t => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116);
  const x = h((0.4124 * R + 0.3576 * G + 0.1805 * B) / 0.95047), y = h(0.2126 * R + 0.7152 * G + 0.0722 * B), z = h((0.0193 * R + 0.1192 * G + 0.9505 * B) / 1.08883);
  return [116 * y - 16, 500 * (x - y), 200 * (y - z)];
}

/* Assign 54 sampled colours to six faces using the centres, keeping exactly nine stickers per face. */
function classifyCube(samples) {
  const order = "URFDLB", lab = samples.map(rgbToLab), centres = [...order].map((_, f) => lab[f * 9 + 4]);
  const dist = (a, b) => (a[0] - b[0]) ** 2 * 0.35 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2;
  const pairs = [];
  lab.forEach((c, i) => centres.forEach((m, f) => pairs.push([dist(c, m), i, f])));
  pairs.sort((a, b) => a[0] - b[0]);
  const out = Array(54).fill(null), used = Array(6).fill(0);
  order.split("").forEach((l, f) => { out[f * 9 + 4] = l; used[f] = 1; });
  for (const [, i, f] of pairs) if (out[i] === null && used[f] < 9) { out[i] = order[f]; used[f]++; }
  return out.join("");
}

if (typeof module !== "undefined") module.exports = { cubeFromFacelets, classifyCube, newCube, applyMove, facelets, SOLVED_CUBE, CUBE_MOVES, solveSudoku };
