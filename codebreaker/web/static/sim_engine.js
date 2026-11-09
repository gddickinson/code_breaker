/* Pure simulation logic with no DOM use, so tests can run it under node. */
const AZ = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const ROTOR_DATA = {
  I: ["EKMFLGDQVZNTOWYHXUSPAIBRCJ", "Q"], II: ["AJDKSIRUXBLHWTMCQGZNPYFVOE", "E"], III: ["BDFHJLCPRTXVZNYEIWGAKMUSQO", "V"],
  IV: ["ESOVPZJAYQUIRHXLNFTGKDCMWB", "J"], V: ["VZBRGITYUPSDNHLXAWMJQOFECK", "Z"],
};
const REFLECTOR_B = "YRUHQSLDPXNGOKMIEBFZCWVJAT";
const idx = c => AZ.indexOf(c);
const mod26 = x => ((x % 26) + 26) % 26;

class Enigma {
  /* rotors, ring and start are ordered left, middle, right. */
  constructor({ rotors = ["I", "II", "III"], ring = "AAA", start = "AAA", plugboard = "" } = {}) {
    this.names = rotors;
    this.wires = rotors.map(n => [...ROTOR_DATA[n][0]].map(idx));
    this.inverse = this.wires.map(w => { const v = []; w.forEach((o, i) => { v[o] = i; }); return v; });
    this.notch = rotors.map(n => idx(ROTOR_DATA[n][1]));
    this.ring = [...ring.toUpperCase()].map(idx);
    this.pos = [...start.toUpperCase()].map(idx);
    this.reflector = [...REFLECTOR_B].map(idx);
    this.plug = [...Array(26).keys()];
    for (const p of plugboard.toUpperCase().split(/\s+/).filter(Boolean)) {
      if (p.length !== 2 || idx(p[0]) < 0 || idx(p[1]) < 0) throw new Error(`Bad plug pair: ${p}`);
      this.plug[idx(p[0])] = idx(p[1]);
      this.plug[idx(p[1])] = idx(p[0]);
    }
  }

  offset(r) { return mod26(this.pos[r] - this.ring[r]); }

  /* Advance the rotors, including the double step of the middle rotor. */
  step() {
    const moved = [false, false, true];
    let note = "The right rotor steps.";
    if (this.pos[1] === this.notch[1]) {
      moved[0] = moved[1] = true;
      this.pos[0] = mod26(this.pos[0] + 1);
      this.pos[1] = mod26(this.pos[1] + 1);
      note = "The middle rotor was at its notch, so it and the left rotor step: the double step.";
    } else if (this.pos[2] === this.notch[2]) {
      moved[1] = true;
      this.pos[1] = mod26(this.pos[1] + 1);
      note = "The right rotor passed its notch, so the middle rotor steps too.";
    }
    this.pos[2] = mod26(this.pos[2] + 1);
    return { moved, note };
  }

  /* One keypress: returns the output letter and every stage of the current path. */
  press(letter) {
    const { moved, note } = this.step();
    const input = idx(letter);
    const stages = [];
    let c = this.plug[input];
    stages.push({ part: "Plugboard", from: input, to: c });
    const forward = [], back = [];
    for (const r of [2, 1, 0]) {
      const o = this.offset(r), out = mod26(this.wires[r][mod26(c + o)] - o);
      stages.push({ part: `Rotor ${this.names[r]}`, from: c, to: out });
      forward.push({ rotor: r, from: c, to: out });
      c = out;
    }
    const reflectFrom = c;
    c = this.reflector[c];
    stages.push({ part: "Reflector B", from: reflectFrom, to: c });
    for (const r of [0, 1, 2]) {
      const o = this.offset(r), out = mod26(this.inverse[r][mod26(c + o)] - o);
      stages.push({ part: `Rotor ${this.names[r]}, returning`, from: c, to: out });
      back.push({ rotor: r, from: c, to: out });
      c = out;
    }
    const output = this.plug[c];
    stages.push({ part: "Plugboard", from: c, to: output });
    return { input, output, letter: AZ[output], stages, forward, back, reflect: [reflectFrom, back[0].from], entry: stages[0].to, exit: c, moved, note, pos: [...this.pos] };
  }

  run(text) { return [...text.toUpperCase()].filter(c => idx(c) >= 0).map(c => this.press(c).letter).join(""); }
}

/* Keyed 5x5 square with J merged into I, matching ciphers/monoalphabetic.square. */
function playfairSquare(keyword) {
  const pool = AZ.replace("J", ""), out = [];
  for (const c of keyword.toUpperCase().replace(/J/g, "I") + pool) if (pool.includes(c) && !out.includes(c)) out.push(c);
  return out.join("");
}

function playfairPairs(text) {
  const t = text.toUpperCase().replace(/[^A-Z]/g, "").replace(/J/g, "I"), out = [];
  let i = 0;
  while (i < t.length) {
    const a = t[i], b = i + 1 < t.length ? t[i + 1] : "X";
    if (a === b) { out.push([a, a !== "X" ? "X" : "Q"]); i += 1; } else { out.push([a, b]); i += 2; }
  }
  return out;
}

function playfairStep(sq, a, b) {
  const p = sq.indexOf(a), q = sq.indexOf(b);
  let [r1, c1, r2, c2] = [Math.floor(p / 5), p % 5, Math.floor(q / 5), q % 5], rule;
  if (r1 === r2) { c1 = (c1 + 1) % 5; c2 = (c2 + 1) % 5; rule = "Same row: each letter moves one step right."; }
  else if (c1 === c2) { r1 = (r1 + 1) % 5; r2 = (r2 + 1) % 5; rule = "Same column: each letter moves one step down."; }
  else { [c1, c2] = [c2, c1]; rule = "Rectangle: each letter takes the corner in its own row."; }
  return { from: [p, q], to: [r1 * 5 + c1, r2 * 5 + c2], out: sq[r1 * 5 + c1] + sq[r2 * 5 + c2], rule };
}

function vigenereTrace(text, key) {
  const k = key.toUpperCase().replace(/[^A-Z]/g, "");
  return [...text.toUpperCase().replace(/[^A-Z]/g, "")].map((p, i) => ({ p, k: k[i % k.length], c: AZ[(idx(p) + idx(k[i % k.length])) % 26] }));
}

function railPattern(n, rails) {
  const period = Math.max(2 * (rails - 1), 1);
  return [...Array(n).keys()].map(i => Math.min(i % period, period - (i % period)));
}

/* Hole positions for a 6x6 turning grille, matching ciphers/transposition._grille_holes. */
function grilleHoles(key) {
  const holes = [];
  let orbit = 0;
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) {
    let p = [r, c];
    for (let t = 0; t < Number(key[orbit]); t++) p = [p[1], 5 - p[0]];
    holes.push(p);
    orbit++;
  }
  return holes;
}
const grilleRotate = holes => holes.map(p => [p[1], 5 - p[0]]);

/* Simulated annealing on a substitution key, scored by trigrams. */
class SubAnneal {
  constructor(cipher, trigrams, total = 45000, seed = 1) {
    this.ct = cipher; this.tri = trigrams; this.total = total; this.done = 0; this.rand = seed >>> 0;
    this.key = [...Array(26).keys()];
    for (let i = 25; i > 0; i--) { const j = Math.floor(this.random() * (i + 1)); [this.key[i], this.key[j]] = [this.key[j], this.key[i]]; }
    this.score = this.evaluate(this.key); this.best = this.score; this.bestKey = [...this.key];
  }
  random() { this.rand = (Math.imul(this.rand, 1664525) + 1013904223) >>> 0; return this.rand / 4294967296; }
  evaluate(k) {
    const c = this.ct, t = this.tri; let s = 0;
    for (let i = 0; i + 2 < c.length; i++) s += t[k[c[i]] * 676 + k[c[i + 1]] * 26 + k[c[i + 2]]];
    return s;
  }
  step(n) {
    for (let i = 0; i < n && this.done < this.total; i++, this.done++) {
      const a = Math.floor(this.random() * 26), b = Math.floor(this.random() * 26);
      [this.key[a], this.key[b]] = [this.key[b], this.key[a]];
      const s = this.evaluate(this.key), temp = 18 * (1 - this.done / this.total) + 0.01;
      if (s >= this.score || this.random() < Math.exp((s - this.score) / temp)) {
        this.score = s;
        if (s > this.best) { this.best = s; this.bestKey = [...this.key]; }
      } else [this.key[a], this.key[b]] = [this.key[b], this.key[a]];
    }
    return this.done >= this.total;
  }
  text(k = this.key) { return this.ct.map(c => AZ[k[c]]).join(""); }
}

if (typeof module !== "undefined") module.exports = { SubAnneal, Enigma, AZ, playfairSquare, playfairPairs, playfairStep, vigenereTrace, railPattern, grilleHoles, grilleRotate };
