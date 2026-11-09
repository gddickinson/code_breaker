/* Pure algorithms for the Theory section. No DOM use, so tests can run them under node. */
const entropyOf = s => { const c = {}; for (const x of s) c[x] = (c[x] || 0) + 1; const n = s.length; return n ? -Object.values(c).reduce((a, v) => a + v / n * Math.log2(v / n), 0) : 0; };
function condEntropy(s) { const pairs = []; for (let i = 0; i + 1 < s.length; i++) pairs.push(s[i] + s[i + 1]); return entropyOf(pairs) - entropyOf([...s].slice(0, -1)); }
const countsOf = s => { const c = {}; for (const x of s) c[x] = (c[x] || 0) + 1; return c; };

function huffman(freq) {
  let nodes = Object.entries(freq).map(([s, w]) => ({ s, w })); const steps = [];
  if (nodes.length === 1) return { codes: { [nodes[0].s]: "0" }, root: nodes[0], steps };
  while (nodes.length > 1) { nodes.sort((a, b) => a.w - b.w || (a.s < b.s ? -1 : 1)); const [a, b] = nodes.splice(0, 2); nodes.push({ s: a.s + b.s, w: a.w + b.w, l: a, r: b }); steps.push([a.s, b.s]); }
  const codes = {}; const walk = (n, p) => { if (n.l) { walk(n.l, p + "0"); walk(n.r, p + "1"); } else codes[n.s] = p; };
  walk(nodes[0], "");
  return { codes, root: nodes[0], steps };
}
function shannonFano(freq) {
  const items = Object.entries(freq).sort((a, b) => b[1] - a[1]), codes = {};
  const split = (arr, p) => { if (arr.length === 1) { codes[arr[0][0]] = p || "0"; return; } const total = arr.reduce((a, x) => a + x[1], 0); let run = 0, cut = 1, best = Infinity; for (let i = 0; i < arr.length - 1; i++) { run += arr[i][1]; const d = Math.abs(total - 2 * run); if (d < best) { best = d; cut = i + 1; } } split(arr.slice(0, cut), p + "0"); split(arr.slice(cut), p + "1"); };
  split(items, ""); return codes;
}
const avgLength = (freq, codes) => { const t = Object.values(freq).reduce((a, b) => a + b, 0); return Object.entries(freq).reduce((a, [s, w]) => a + w * codes[s].length, 0) / t; };
const encode = (s, codes) => [...s].map(c => codes[c]).join("");
function decodePrefix(bits, codes) { const inv = Object.fromEntries(Object.entries(codes).map(([k, v]) => [v, k])); let out = "", cur = ""; for (const b of bits) { cur += b; if (inv[cur] !== undefined) { out += inv[cur]; cur = ""; } } return out; }

function rng(seed) { let s = seed >>> 0; return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; }; }
function makeBits(kind, n, seed) { const o = []; if (kind === "good") { let a = seed >>> 0; for (let i = 0; i < n; i++) { a = (a + 0x6d2b79f5) >>> 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; o.push(((t ^ (t >>> 14)) >>> 31) & 1); } } else if (kind === "biased") { const r = rng(seed); for (let i = 0; i < n; i++) o.push(r() < 0.56 ? 1 : 0); } else if (kind === "lcg") { let x = seed || 1; for (let i = 0; i < n; i++) { x = (x * 13 + 7) % 256; o.push(x & 1); } } else { let x = 1; for (let i = 0; i < n; i++) { o.push(i % 2); x++; } } return o; }
function randomnessTests(b) {
  const n = b.length, ones = b.reduce((a, v) => a + v, 0), mono = Math.abs(2 * ones - n) / Math.sqrt(n), pi = ones / n;
  let runs = 1; for (let i = 1; i < n; i++) if (b[i] !== b[i - 1]) runs++;
  const expect = 2 * n * pi * (1 - pi), runZ = Math.abs(runs - expect) / (2 * Math.sqrt(2 * n) * pi * (1 - pi) || 1);
  const c = [0, 0, 0, 0]; for (let i = 0; i + 1 < n; i += 2) c[b[i] * 2 + b[i + 1]]++; const pairs = Math.floor(n / 2), chi = c.reduce((a, v) => a + (v - pairs / 4) ** 2 / (pairs / 4), 0);
  let corr = 0; for (let i = 1; i < n; i++) corr += b[i] === b[i - 1] ? 1 : -1;
  return { ones: pi, monobit: mono, runs, runZ, pairChi: chi, lag1: corr / (n - 1), pass: { monobit: mono < 2.58, runs: runZ < 2.58, pairs: chi < 11.34 } };
}
function lfsr(taps, seedBits, n) { const s = [...seedBits], out = []; for (let i = 0; i < n; i++) { out.push(s[s.length - 1]); const f = taps.reduce((a, t) => a ^ s[s.length - 1 - t], 0); s.pop(); s.unshift(f); } return out; }
function berlekampMassey(s) { let C = [1], B = [1], L = 0, m = 1; for (let n = 0; n < s.length; n++) { let d = s[n]; for (let i = 1; i <= L; i++) d ^= (C[i] || 0) & s[n - i]; if (!d) m++; else { const T = [...C]; const sh = Array(m).fill(0).concat(B); for (let i = 0; i < sh.length; i++) C[i] = (C[i] || 0) ^ sh[i]; if (2 * L <= n) { L = n + 1 - L; B = T; m = 1; } else m++; } } return { L, C }; }
function bmPredict(s, C, L, n) { const out = [...s]; for (let i = s.length; i < s.length + n; i++) { let v = 0; for (let j = 1; j <= L; j++) v ^= (C[j] || 0) & out[i - j]; out.push(v); } return out.slice(s.length); }

function monteCarloPi(n, seed) { const r = rng(seed); let inside = 0; const pts = []; for (let i = 0; i < n; i++) { const x = r(), y = r(), a = x * x + y * y <= 1; if (a) inside++; if (i < 900) pts.push([x, y, a]); } return { estimate: 4 * inside / n, pts }; }
function metropolis(target, n, step, seed, start = 0) { const r = rng(seed); let x = start, acc = 0; const out = []; for (let i = 0; i < n; i++) { const y = x + (r() - 0.5) * 2 * step, a = target(y) / target(x); if (r() < a) { x = y; acc++; } out.push(x); } return { samples: out, acceptance: acc / n }; }

/* Sum-product on a parity-check code, over a binary symmetric channel. */
const HAMMING = [[1, 1, 0, 1, 1, 0, 0], [1, 0, 1, 1, 0, 1, 0], [0, 1, 1, 1, 0, 0, 1]];
function bpDecode(llr, H = HAMMING, iters = 12) {
  const M = H.length, N = H[0].length, v2c = {}, c2v = {}, key = (a, b) => `${a},${b}`;
  H.forEach((r, c) => r.forEach((v, n) => { if (v) { v2c[key(n, c)] = llr[n]; c2v[key(c, n)] = 0; } }));
  const history = []; let post = [...llr];
  for (let it = 0; it < iters; it++) {
    for (let c = 0; c < M; c++) { const ns = H[c].flatMap((v, n) => (v ? [n] : [])); for (const n of ns) { let p = 1; for (const o of ns) if (o !== n) p *= Math.tanh(v2c[key(o, c)] / 2); p = Math.max(-0.999999, Math.min(0.999999, p)); c2v[key(c, n)] = 2 * Math.atanh(p); } }
    post = llr.map((l, n) => l + H.reduce((a, r, c) => a + (r[n] ? c2v[key(c, n)] : 0), 0));
    for (let n = 0; n < N; n++) for (let c = 0; c < M; c++) if (H[c][n]) v2c[key(n, c)] = post[n] - c2v[key(c, n)];
    history.push([...post]);
  }
  return { bits: post.map(v => (v < 0 ? 1 : 0)), posterior: post, history };
}
const parityOK = (b, H = HAMMING) => H.every(r => r.reduce((a, v, i) => a ^ (v & b[i]), 0) === 0);

/* Hidden Markov model: forward-backward for each letter, and Viterbi for the single best path. */
function hmmDecode(obs, trans, emit) {
  const S = 26, T = obs.length, F = Array.from({ length: T }, () => Array(S).fill(0)), B = Array.from({ length: T }, () => Array(S).fill(1));
  for (let s = 0; s < S; s++) F[0][s] = emit(s, obs[0]) / S;
  for (let t = 1; t < T; t++) { let z = 0; for (let s = 0; s < S; s++) { let a = 0; for (let p = 0; p < S; p++) a += F[t - 1][p] * trans[p][s]; F[t][s] = a * emit(s, obs[t]); z += F[t][s]; } for (let s = 0; s < S; s++) F[t][s] /= z; }
  for (let t = T - 2; t >= 0; t--) { let z = 0; for (let s = 0; s < S; s++) { let a = 0; for (let n = 0; n < S; n++) a += trans[s][n] * emit(n, obs[t + 1]) * B[t + 1][n]; B[t][s] = a; z += a; } for (let s = 0; s < S; s++) B[t][s] /= z; }
  return F.map((f, t) => { let b = 0, bv = -1; f.forEach((v, s) => { const p = v * B[t][s]; if (p > bv) { bv = p; b = s; } }); return b; });
}
function viterbi(obs, trans, emit) {
  const S = 26, T = obs.length, V = [Array.from({ length: S }, (_, s) => Math.log(emit(s, obs[0])))], back = [];
  for (let t = 1; t < T; t++) { const v = Array(S), bk = Array(S); for (let s = 0; s < S; s++) { let b = 0, bv = -Infinity; for (let p = 0; p < S; p++) { const x = V[t - 1][p] + Math.log(trans[p][s]); if (x > bv) { bv = x; b = p; } } v[s] = bv + Math.log(emit(s, obs[t])); bk[s] = b; } V.push(v); back.push(bk); }
  let cur = V[T - 1].indexOf(Math.max(...V[T - 1])); const path = [cur]; for (let t = T - 2; t >= 0; t--) { cur = back[t][cur]; path.unshift(cur); } return path;
}

/* Ising image denoising: Gibbs sampling against mean-field variational inference. */
function isingData(n, flip, seed) { const r = rng(seed), clean = [], noisy = []; for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) { const on = (x - n / 2) ** 2 + (y - n / 2) ** 2 < (n * 0.32) ** 2 && !(Math.abs(x - n / 2) < n * 0.1); const v = on ? 1 : -1; clean.push(v); noisy.push(r() < flip ? -v : v); } return { clean, noisy }; }
const nbrs = (i, n) => { const y = Math.floor(i / n), x = i % n, o = []; if (x > 0) o.push(i - 1); if (x < n - 1) o.push(i + 1); if (y > 0) o.push(i - n); if (y < n - 1) o.push(i + n); return o; };
function meanField(noisy, n, J, h, iters) { const q = noisy.map(v => v * 0.5); const hist = [[...q]]; for (let t = 0; t < iters; t++) { for (let i = 0; i < n * n; i++) q[i] = Math.tanh(h * noisy[i] + J * nbrs(i, n).reduce((a, j) => a + q[j], 0)); hist.push([...q]); } return { q, hist }; }
function gibbs(noisy, n, J, h, sweeps, seed) { const r = rng(seed), s = [...noisy], avg = Array(n * n).fill(0); const burn = Math.floor(sweeps / 3); for (let t = 0; t < sweeps; t++) { for (let i = 0; i < n * n; i++) { const f = h * noisy[i] + J * nbrs(i, n).reduce((a, j) => a + s[j], 0); s[i] = r() < (1 + Math.tanh(f)) / 2 ? 1 : -1; if (t >= burn) avg[i] += s[i]; } } return avg.map(v => v / (sweeps - burn)); }
const agreement = (a, b) => a.reduce((n, v, i) => n + (Math.sign(v) === Math.sign(b[i]) ? 1 : 0), 0) / a.length;

/* Shor period finding, simulated on a state vector with a discrete Fourier transform. */
const gcd2 = (a, b) => { while (b) [a, b] = [b, a % b]; return a; };
function modPow(b, e, m) { let r = 1; b %= m; while (e) { if (e & 1) r = r * b % m; b = b * b % m; e = Math.floor(e / 2); } return r; }
function shorProbs(N, a, qubits) { const Q = 2 ** qubits, ys = new Map(); for (let x = 0; x < Q; x++) { const f = modPow(a, x, N); if (!ys.has(f)) ys.set(f, []); ys.get(f).push(x); } const p = Array(Q).fill(0); for (const xs of ys.values()) for (let k = 0; k < Q; k++) { let re = 0, im = 0; for (const x of xs) { const t = 2 * Math.PI * x * k / Q; re += Math.cos(t); im += Math.sin(t); } p[k] += (re * re + im * im) / (Q * Q); } return p; }
function bestDenominator(k, Q, N) { let [n0, d0, n1, d1, a, b] = [0, 1, 1, 0, k, Q]; let best = 1; while (b) { const c = Math.floor(a / b); [n0, n1] = [n1, c * n1 + n0]; [d0, d1] = [d1, c * d1 + d0]; [a, b] = [b, a - c * b]; if (d1 > 0 && d1 < N) best = d1; else break; } return best; }
function shorFactor(N, a, qubits, seed) { const g = gcd2(a, N); if (g > 1) return { factors: [g, N / g], tries: 0, classical: true }; const p = shorProbs(N, a, qubits), r0 = rng(seed), Q = 2 ** qubits; for (let t = 1; t <= 40; t++) { let u = r0(), k = 0; for (; k < Q - 1; k++) { u -= p[k]; if (u <= 0) break; } if (k === 0) continue; const d = bestDenominator(k, Q, N); for (let m = 1; m <= 6; m++) { const r = d * m; if (r < N && modPow(a, r, N) === 1 && r % 2 === 0) { const h = modPow(a, r / 2, N); if (h !== N - 1) { const f = gcd2(h + 1, N); if (f > 1 && f < N) return { factors: [f, N / f], tries: t, r, k }; } } } } return { factors: null }; }

/* Differential cryptanalysis of a toy 4-bit cipher using the PRESENT S-box. */
const SB = [12, 5, 6, 11, 9, 0, 10, 13, 3, 14, 15, 8, 4, 7, 1, 2], SBI = SB.reduce((a, v, i) => { a[v] = i; return a; }, []);
function ddt() { const t = Array.from({ length: 16 }, () => Array(16).fill(0)); for (let d = 0; d < 16; d++) for (let x = 0; x < 16; x++) t[d][SB[x] ^ SB[x ^ d]]++; return t; }
const toyEnc = (p, k) => SB[SB[p ^ k[0]] ^ k[1]] ^ k[2];
function diffAttack(k) { const t = ddt(), counts = Array(16).fill(0); for (let dx = 1; dx < 16; dx++) { const dy = t[dx].indexOf(Math.max(...t[dx])); for (let g = 0; g < 16; g++) for (let x = 0; x < 16; x++) { const c1 = toyEnc(x, k), c2 = toyEnc(x ^ dx, k); if ((SBI[c1 ^ g] ^ SBI[c2 ^ g]) === dy) counts[g]++; } } return counts; }

/* Pollard's rho: a pseudo-random walk that finds a factor when it cycles modulo that factor. */
function pollardRho(n, c = 1) { const f = x => (x * x + c) % n; let a = 2, b = 2, steps = 0; const path = []; while (steps < 100000) { a = f(a); b = f(f(b)); steps++; path.push(a); const d = gcd2(Math.abs(a - b), n); if (d === n) return { factor: null, steps }; if (d > 1) return { factor: d, steps, path: path.slice(0, 160) }; } return { factor: null, steps }; }

if (typeof module !== "undefined") module.exports = { entropyOf, condEntropy, countsOf, huffman, shannonFano, avgLength, encode, decodePrefix, rng, makeBits, randomnessTests, lfsr, berlekampMassey, bmPredict, monteCarloPi, metropolis, HAMMING, bpDecode, parityOK, hmmDecode, viterbi, isingData, meanField, gibbs, agreement, shorProbs, shorFactor, modPow, ddt, diffAttack, toyEnc, pollardRho };
