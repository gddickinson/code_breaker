/* Notes on a treble stave, and playback (Round 81). Tokens: note names such as A, B♭, B♮, E♭, C♯4; "|" is a bar
   line. Without an octave, A and B sit in octave 4 and C-G in octave 5, so a cryptogram stays on the staff. */
const MUSIC_STEP = { C: 0, D: 1, E: 2, F: 3, G: 4, A: 5, B: 6 };
const MUSIC_SEMI = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };

function musicParse(text) {
  return String(text).replace(/\|/g, " | ").split(/\s+/).filter(Boolean).map(t => {
    if (t === "|") return { bar: true };
    const m = t.match(/^([A-G])([♭♮♯#b]?)(\d)?$/);
    if (!m) return null;
    const oct = m[3] ? +m[3] : (m[1] === "A" || m[1] === "B" ? 4 : 5);
    const acc = m[2] === "#" ? "♯" : m[2] === "b" ? "♭" : m[2];
    return { name: m[1], acc, oct, label: t };
  }).filter(Boolean);
}

function musicFreq(n) {
  const semi = MUSIC_SEMI[n.name] + (n.acc === "♯" ? 1 : n.acc === "♭" ? -1 : 0) + (n.oct - 4) * 12;
  return 261.63 * Math.pow(2, semi / 12);  // C4 = middle C
}

function musicSVG(text) {
  const notes = musicParse(text).slice(0, 120), dx = 30, w = 60 + notes.length * dx, top = 30, gap = 10;
  const yOf = n => top + 4 * gap - ((n.oct - 4) * 7 + MUSIC_STEP[n.name] - 2) * gap / 2;  // E4 on the bottom line
  let s = `<svg viewBox="0 0 ${w} 120" width="${Math.min(w, 960)}" role="img" aria-label="${esc(notes.filter(n => !n.bar).map(n => n.label).join(" "))}" style="max-width:100%;background:#f7f4ea;border-radius:4px">`;
  for (let i = 0; i < 5; i++) s += `<line x1="8" x2="${w - 8}" y1="${top + i * gap}" y2="${top + i * gap}" stroke="#333" stroke-width="1"/>`;
  s += `<text x="10" y="${top + 34}" font-size="44" font-family="serif" fill="#333">𝄞</text>`;
  notes.forEach((n, i) => {
    const x = 50 + i * dx;
    if (n.bar) { s += `<line x1="${x}" x2="${x}" y1="${top}" y2="${top + 4 * gap}" stroke="#333"/>`; return; }
    const y = yOf(n);
    for (let ly = top + 5 * gap; ly <= y; ly += gap) s += `<line x1="${x - 9}" x2="${x + 9}" y1="${ly}" y2="${ly}" stroke="#333"/>`;
    for (let ly = top - gap; ly >= y; ly -= gap) s += `<line x1="${x - 9}" x2="${x + 9}" y1="${ly}" y2="${ly}" stroke="#333"/>`;
    if (n.acc) s += `<text x="${x - 18}" y="${y + 5}" font-size="15" fill="#333">${n.acc}</text>`;
    s += `<ellipse cx="${x}" cy="${y}" rx="6" ry="4.5" transform="rotate(-20 ${x} ${y})" fill="#111"/>`;
    s += `<line x1="${x + 5.5}" x2="${x + 5.5}" y1="${y}" y2="${y - 30}" stroke="#111" stroke-width="1.3"/>`;
  });
  return s + "</svg>";
}

let musicCtx = null;
function musicPlay(text, tempo = 0.32) {
  musicCtx = musicCtx || new (window.AudioContext || window.webkitAudioContext)();
  let t = musicCtx.currentTime + 0.05;
  musicParse(text).forEach(n => {
    if (n.bar) { t += tempo / 2; return; }
    const o = musicCtx.createOscillator(), g = musicCtx.createGain();
    o.type = "triangle"; o.frequency.value = musicFreq(n);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.25, t + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, t + tempo * 0.95);
    o.connect(g).connect(musicCtx.destination); o.start(t); o.stop(t + tempo);
    t += tempo;
  });
}

/* A stave with a play button, for any element; used on the Library pages of the Music family. */
function musicPanel(text, id) {
  return `<div class="stave">${musicSVG(text)}</div><button class="alt" id="${id}">▶ Play</button>`;
}
