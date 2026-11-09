/* Pure AES-128, S-DES and Colossus-model logic with no DOM use, so tests can run it under node. */
const SBOX = (() => {
  const box = new Uint8Array(256); let p = 1, q = 1;
  do {
    p = p ^ ((p << 1) & 255) ^ (p & 128 ? 27 : 0);
    q ^= q << 1; q ^= q << 2; q ^= q << 4; q &= 255; if (q & 128) q ^= 9;
    const r = (x, n) => ((x << n) | (x >> (8 - n))) & 255;
    box[p] = q ^ r(q, 1) ^ r(q, 2) ^ r(q, 3) ^ r(q, 4) ^ 99;
  } while (p !== 1);
  box[0] = 99;
  return box;
})();
const xt = a => ((a << 1) ^ (a & 128 ? 27 : 0)) & 255;
const hex = b => [...b].map(x => x.toString(16).padStart(2, "0")).join("");
const unhex = h => Uint8Array.from(h.match(/../g).map(x => parseInt(x, 16)));

function expandKey(key) {
  const w = [...key]; let rcon = 1;
  for (let i = 16; i < 176; i += 4) {
    let t = w.slice(i - 4, i);
    if (i % 16 === 0) { t = [SBOX[t[1]] ^ rcon, SBOX[t[2]], SBOX[t[3]], SBOX[t[0]]]; rcon = xt(rcon); }
    for (let j = 0; j < 4; j++) w[i + j] = w[i - 16 + j] ^ t[j];
  }
  return w;
}
const addKey = (s, w, r) => s.map((v, i) => v ^ w[r * 16 + i]);
const subBytes = s => s.map(v => SBOX[v]);
const shiftRows = s => s.map((_, i) => s[(i + 4 * (i % 4)) % 16]);
function mixColumns(s) {
  const o = [...s];
  for (let c = 0; c < 16; c += 4) {
    const [a, b, d, e] = s.slice(c, c + 4);
    o[c] = xt(a) ^ xt(b) ^ b ^ d ^ e; o[c + 1] = a ^ xt(b) ^ xt(d) ^ d ^ e;
    o[c + 2] = a ^ b ^ xt(d) ^ xt(e) ^ e; o[c + 3] = xt(a) ^ a ^ b ^ d ^ xt(e);
  }
  return o;
}

/* Every intermediate state, for the round-by-round view. */
function aesTrace(block, key) {
  const w = expandKey(key), steps = [];
  let s = addKey([...block], w, 0);
  steps.push({ round: 0, op: "AddRoundKey", state: s });
  for (let r = 1; r <= 10; r++) {
    s = subBytes(s); steps.push({ round: r, op: "SubBytes", state: s });
    s = shiftRows(s); steps.push({ round: r, op: "ShiftRows", state: s });
    if (r < 10) { s = mixColumns(s); steps.push({ round: r, op: "MixColumns", state: s }); }
    s = addKey(s, w, r); steps.push({ round: r, op: "AddRoundKey", state: s });
  }
  return steps;
}
const aesEncrypt = (block, key) => aesTrace(block, key).at(-1).state;

/* S-DES, matching ciphers/modern_symmetric.py. */
const perm = (b, t) => t.map(i => b[i - 1]);
const toBits = (v, n) => [...Array(n).keys()].map(i => (v >> (n - 1 - i)) & 1);
const fromBits = b => b.reduce((a, x) => a * 2 + x, 0);
const S0 = [[1, 0, 3, 2], [3, 2, 1, 0], [0, 2, 1, 3], [3, 1, 3, 2]], S1 = [[0, 1, 2, 3], [2, 0, 1, 3], [3, 0, 1, 0], [2, 1, 0, 3]];
function sdesTrace(v, key) {
  const k10 = perm(toBits(key, 10), [3, 5, 2, 7, 4, 10, 1, 9, 8, 6]);
  const L = k10.slice(0, 5), R = k10.slice(5), rot = (x, n) => x.slice(n).concat(x.slice(0, n));
  const l1 = rot(L, 1), r1 = rot(R, 1), P8 = [6, 3, 7, 4, 8, 5, 10, 9];
  const k1 = perm(l1.concat(r1), P8), k2 = perm(rot(l1, 2).concat(rot(r1, 2)), P8);
  const fk = (b, k) => {
    const l = b.slice(0, 4), r = b.slice(4), t = perm(r, [4, 1, 2, 3, 2, 3, 4, 1]).map((x, i) => x ^ k[i]);
    const p = perm(toBits(S0[t[0] * 2 + t[3]][t[1] * 2 + t[2]], 2).concat(toBits(S1[t[4] * 2 + t[7]][t[5] * 2 + t[6]], 2)), [2, 4, 3, 1]);
    return l.map((x, i) => x ^ p[i]).concat(r);
  };
  const ip = perm(toBits(v, 8), [2, 6, 3, 1, 4, 8, 5, 7]), a = fk(ip, k1), sw = a.slice(4).concat(a.slice(0, 4)), b = fk(sw, k2), out = perm(b, [4, 1, 3, 5, 7, 2, 8, 6]);
  return { steps: [["Input", toBits(v, 8)], ["Initial permutation", ip], ["Round 1 (key " + k1.join("") + ")", a], ["Swap halves", sw], ["Round 2 (key " + k2.join("") + ")", b], ["Final permutation", out]], out: fromBits(out) };
}

/* Colossus teaching model: count agreements between a biased message stream and each wheel start. */
function makeRng(seed) { let s = seed >>> 0; return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; }; }
function colossusTape(wheel, trueStart, length, bias, seed) {
  const r = makeRng(seed);
  return [...Array(length).keys()].map(i => (r() < bias ? 0 : 1) ^ wheel[(trueStart + i) % wheel.length]);
}
function colossusCount(tape, wheel) { return wheel.map((_, s) => tape.reduce((n, b, i) => n + (b === wheel[(s + i) % wheel.length] ? 1 : 0), 0)); }

/* Square-and-multiply steps for the RSA view. */
function modPowSteps(base, exp, mod) {
  const bits = exp.toString(2), steps = []; let r = 1;
  for (const b of bits) { r = (r * r) % mod; const sq = r; if (b === "1") r = (r * base) % mod; steps.push({ bit: b, squared: sq, value: r }); }
  return { bits, steps, value: r };
}

if (typeof module !== "undefined") module.exports = { aesTrace, aesEncrypt, hex, unhex, sdesTrace, colossusTape, colossusCount, modPowSteps };

/* Least-significant-bit steganography, over RGB bytes: a 16-bit length, then UTF-8 text. */
function lsbEmbed(pixels, text) {
  const data = new TextEncoder().encode(text), bits = [];
  for (let i = 15; i >= 0; i--) bits.push((data.length >> i) & 1);
  data.forEach(b => { for (let i = 7; i >= 0; i--) bits.push((b >> i) & 1); });
  if (bits.length > pixels.length) throw new Error("Message is too long for this image.");
  const out = Uint8Array.from(pixels);
  bits.forEach((b, i) => { out[i] = (out[i] & 254) | b; });
  return out;
}
function lsbExtract(pixels) {
  let n = 0; for (let i = 0; i < 16; i++) n = n * 2 + (pixels[i] & 1);
  const out = new Uint8Array(n);
  for (let i = 0; i < n; i++) { let v = 0; for (let j = 0; j < 8; j++) v = v * 2 + (pixels[16 + i * 8 + j] & 1); out[i] = v; }
  return new TextDecoder().decode(out);
}
if (typeof module !== "undefined") Object.assign(module.exports, { lsbEmbed, lsbExtract });
