/* Error-detecting and error-correcting codes: pure functions, tested in node. */
const ECC_PARITY = bits => bits.reduce((a, b) => a ^ b, 0);

function crcBits(bits, poly) {
  /* Remainder of the message (with zeros appended) divided by the generator polynomial, in binary. */
  const n = poly.length - 1, r = [...bits, ...Array(n).fill(0)];
  for (let i = 0; i < bits.length; i++) if (r[i]) for (let j = 0; j < poly.length; j++) r[i + j] ^= poly[j];
  return r.slice(-n);
}
const CRC8 = [1, 0, 0, 0, 0, 0, 1, 1, 1];
const textBits = s => [...new TextEncoder().encode(s)].flatMap(b => [7, 6, 5, 4, 3, 2, 1, 0].map(i => (b >> i) & 1));

function luhnValid(digits) {
  const d = digits.replace(/\D/g, "").split("").reverse().map(Number);
  return d.length > 1 && d.reduce((a, v, i) => a + (i % 2 ? (v * 2 > 9 ? v * 2 - 9 : v * 2) : v), 0) % 10 === 0;
}
function isbn10Valid(s) {
  const c = s.replace(/[^0-9X]/gi, "").toUpperCase();
  return c.length === 10 && [...c].reduce((a, ch, i) => a + (ch === "X" ? 10 : +ch) * (10 - i), 0) % 11 === 0;
}

/* Hamming(7,4): positions 1..7, parity bits at 1, 2 and 4; the syndrome is the position of a single error. */
function hamming74Encode(d) {
  const [d1, d2, d3, d4] = d;
  return [d1 ^ d2 ^ d4, d1 ^ d3 ^ d4, d1, d2 ^ d3 ^ d4, d2, d3, d4];
}
function hamming74Decode(c) {
  const s = [0, 1, 2].reduce((a, k) => a | (c.reduce((x, v, i) => x ^ (((i + 1) >> k) & 1 ? v : 0), 0) << k), 0);
  const fixed = [...c];
  if (s) fixed[s - 1] ^= 1;
  return { syndrome: s, corrected: fixed, data: [fixed[2], fixed[4], fixed[5], fixed[6]] };
}

/* Reed-Solomon over GF(256) with the QR-code polynomial 0x11d: Berlekamp-Massey, Chien search and Forney. */
const GF_EXP = new Array(512), GF_LOG = new Array(256).fill(0);
(() => { let x = 1; for (let i = 0; i < 255; i++) { GF_EXP[i] = x; GF_LOG[x] = i; x <<= 1; if (x & 0x100) x ^= 0x11d; } for (let i = 255; i < 512; i++) GF_EXP[i] = GF_EXP[i - 255]; })();
const gfMul = (a, b) => (a && b ? GF_EXP[GF_LOG[a] + GF_LOG[b]] : 0);
const gfDiv = (a, b) => (a ? GF_EXP[(GF_LOG[a] + 255 - GF_LOG[b]) % 255] : 0);
const gfPow = (a, p) => GF_EXP[(((GF_LOG[a] * p) % 255) + 255) % 255];
const gfInv = a => GF_EXP[255 - GF_LOG[a]];
const polyScale = (p, x) => p.map(c => gfMul(c, x));
function polyAdd(p, q) { const r = Array(Math.max(p.length, q.length)).fill(0); p.forEach((c, i) => { r[i + r.length - p.length] = c; }); q.forEach((c, i) => { r[i + r.length - q.length] ^= c; }); return r; }
function polyMul(p, q) { const r = Array(p.length + q.length - 1).fill(0); for (let i = 0; i < p.length; i++) for (let j = 0; j < q.length; j++) r[i + j] ^= gfMul(p[i], q[j]); return r; }
function polyEval(p, x) { let y = p[0]; for (let i = 1; i < p.length; i++) y = gfMul(y, x) ^ p[i]; return y; }
function polyDivRem(a, d) { const o = [...a]; for (let i = 0; i < a.length - (d.length - 1); i++) { const c = o[i]; if (c) for (let j = 1; j < d.length; j++) if (d[j]) o[i + j] ^= gfMul(d[j], c); } return o.slice(o.length - (d.length - 1)); }

function rsEncode(msg, nsym) {
  let g = [1];
  for (let i = 0; i < nsym; i++) g = polyMul(g, [1, gfPow(2, i)]);
  const out = [...msg, ...Array(nsym).fill(0)];
  for (let i = 0; i < msg.length; i++) { const c = out[i]; if (c) for (let j = 1; j < g.length; j++) out[i + j] ^= gfMul(g[j], c); }
  return [...msg, ...out.slice(msg.length)];
}

function rsDecode(msgIn, nsym) {
  const msg = [...msgIn];
  const synd = [0, ...Array.from({ length: nsym }, (_, i) => polyEval(msg, gfPow(2, i)))];
  if (synd.every(v => v === 0)) return { ok: true, data: msg.slice(0, msg.length - nsym), errors: [] };
  let loc = [1], old = [1];
  for (let i = 0; i < nsym; i++) {
    const K = i + 1;
    let delta = synd[K];
    for (let j = 1; j < loc.length; j++) delta ^= gfMul(loc[loc.length - 1 - j], synd[K - j]);
    old = [...old, 0];
    if (delta) {
      if (old.length > loc.length) { const nl = polyScale(old, delta); old = polyScale(loc, gfInv(delta)); loc = nl; }
      loc = polyAdd(loc, polyScale(old, delta));
    }
  }
  while (loc.length && loc[0] === 0) loc.shift();
  const errs = loc.length - 1;
  if (errs * 2 > nsym) return { ok: false, reason: "too many errors", data: null, errors: [] };
  const rev = [...loc].reverse(), pos = [];
  for (let i = 0; i < msg.length; i++) if (polyEval(rev, gfPow(2, i)) === 0) pos.push(msg.length - 1 - i);
  if (pos.length !== errs) return { ok: false, reason: "errors could not be located", data: null, errors: [] };
  const coef = pos.map(p => msg.length - 1 - p);
  let eloc = [1];
  coef.forEach(i => { eloc = polyMul(eloc, polyAdd([1], [gfPow(2, i), 0])); });
  const evalPoly = polyDivRem(polyMul([...synd].reverse(), eloc), [1, ...Array(eloc.length).fill(0)]).reverse();
  const X = coef.map(i => gfPow(2, -(255 - i)));
  const E = Array(msg.length).fill(0);
  X.forEach((Xi, i) => {
    const Xinv = gfInv(Xi);
    let prime = 1;
    X.forEach((Xj, j) => { if (j !== i) prime = gfMul(prime, 1 ^ gfMul(Xinv, Xj)); });
    const y = gfMul(Xi, polyEval([...evalPoly].reverse(), Xinv));
    E[pos[i]] = gfDiv(y, prime);
  });
  const fixed = polyAdd(msg, E);
  const check = Array.from({ length: nsym }, (_, i) => polyEval(fixed, gfPow(2, i)));
  if (check.some(v => v)) return { ok: false, reason: "decoding failed the final check", data: null, errors: [] };
  return { ok: true, data: fixed.slice(0, fixed.length - nsym), errors: pos.sort((a, b) => a - b) };
}

/* Convolutional code, rate 1/2, constraint length 3, generators 7 and 5 (octal); hard-decision Viterbi decoding. */
function convEncode(bits) {
  let s = 0;
  const out = [];
  for (const b of [...bits, 0, 0]) { const r = (b << 2) | s; out.push(ECC_PARITY([(r >> 2) & 1, (r >> 1) & 1, r & 1]), ECC_PARITY([(r >> 2) & 1, r & 1])); s = r >> 1; }
  return out;
}
function viterbiDecode(rx) {
  const n = rx.length / 2, INF = 1e9;
  let metric = [0, INF, INF, INF];
  const back = [];
  for (let t = 0; t < n; t++) {
    const nm = [INF, INF, INF, INF], bp = [0, 0, 0, 0];
    for (let s = 0; s < 4; s++) {
      if (metric[s] >= INF) continue;
      for (const b of [0, 1]) {
        const r = (b << 2) | s, o0 = ECC_PARITY([(r >> 2) & 1, (r >> 1) & 1, r & 1]), o1 = ECC_PARITY([(r >> 2) & 1, r & 1]), ns = r >> 1;
        const m = metric[s] + (o0 !== rx[2 * t]) + (o1 !== rx[2 * t + 1]);
        if (m < nm[ns]) { nm[ns] = m; bp[ns] = s * 2 + b; }
      }
    }
    back.push(bp);
    metric = nm;
  }
  let s = 0;
  const bits = [];
  for (let t = n - 1; t >= 0; t--) { const v = back[t][s]; bits.push(v & 1); s = v >> 1; }
  return bits.reverse().slice(0, n - 2);
}

function eccRng(seed) { let s = seed >>> 0; return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; }; }
const flipChannel = (bits, p, r) => bits.map(b => (r() < p ? b ^ 1 : b));
const binEntropy = p => (p <= 0 || p >= 1 ? 0 : -p * Math.log2(p) - (1 - p) * Math.log2(1 - p));

function berCompare(p, n = 4000, seed = 1) {
  /* Bit error rate after a binary symmetric channel with flip probability p, for four schemes. */
  const r = eccRng(seed), data = Array.from({ length: n }, () => (r() < 0.5 ? 1 : 0));
  const errs = (a, b) => a.reduce((x, v, i) => x + (v !== b[i]), 0) / a.length;
  const raw = flipChannel(data, p, r);
  const rep = data.map(b => { const k = flipChannel([b, b, b], p, r); return k[0] + k[1] + k[2] >= 2 ? 1 : 0; });
  const ham = [];
  for (let i = 0; i + 4 <= n; i += 4) ham.push(...hamming74Decode(flipChannel(hamming74Encode(data.slice(i, i + 4)), p, r)).data);
  const conv = viterbiDecode(flipChannel(convEncode(data), p, r));
  return { p, capacity: 1 - binEntropy(p), schemes: [{ name: "No coding", rate: 1, ber: errs(raw, data) }, { name: "Hamming(7,4)", rate: 4 / 7, ber: errs(ham, data) }, { name: "Convolutional + Viterbi", rate: 1 / 2, ber: errs(conv, data) }, { name: "Repeat three times", rate: 1 / 3, ber: errs(rep, data) }] };
}

if (typeof module !== "undefined") module.exports = { crcBits, CRC8, textBits, luhnValid, isbn10Valid, hamming74Encode, hamming74Decode, rsEncode, rsDecode, convEncode, viterbiDecode, berCompare, binEntropy, eccRng };
