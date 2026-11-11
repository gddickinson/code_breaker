/* Lens overlay: neon brackets, labels, a sweeping scan line and lock-on animation, drawn over a video or picture. */
const LENS_COLORS = { object: "#7CFC00", text: "#00f0ff", code: "#f5e642", sign: "#ff2a6d", lsb: "#ff5c7a", trailing: "#ff5c7a", embedded: "#ff5c7a", metadata: "#c084fc",
  zero_width: "#ff5c7a", whitespace: "#ff5c7a", homoglyph: "#ff5c7a", acrostic: "#39ff88" };
const lensOv = { canvas: null, items: [], born: 0, sweep: 0, raf: 0, scale: 1, status: "", hud: [], dx: 0, dy: 0 };

function lensOverlayStart(canvas) {
  lensOv.canvas = canvas;
  cancelAnimationFrame(lensOv.raf);
  const tick = t => { lensDraw(t); lensOv.raf = requestAnimationFrame(tick); };
  lensOv.raf = requestAnimationFrame(tick);
}

function lensOverlayStop() { cancelAnimationFrame(lensOv.raf); lensOv.raf = 0; }

function lensIou(a, b) {
  const ix = Math.max(0, Math.min(a[0] + a[2], b[0] + b[2]) - Math.max(a[0], b[0])), iy = Math.max(0, Math.min(a[1] + a[3], b[1] + b[3]) - Math.max(a[1], b[1]));
  const i = ix * iy; return i / Math.max(1, a[2] * a[3] + b[2] * b[3] - i);
}

/* track: keep findings across live frames; a finding matched by label and position moves smoothly, an unmatched
   one fades and is dropped after three missed frames. A still picture (track=false) replaces everything. */
function lensOverlaySet(findings, srcW, status, track = false) {
  const c = lensOv.canvas;
  if (!c) return;
  lensOv.scale = c.width / Math.max(1, srcW);
  const fresh = findings.filter(f => f.box);
  if (!track) { lensOv.items = fresh.map(f => ({ ...f, miss: 0, born: performance.now() })); }
  else {
    const now = performance.now(), used = new Set();
    lensOv.items.forEach(it => {
      let best = -1, bi = 0.15;
      fresh.forEach((f, j) => { if (used.has(j)) return; const s = lensIou(it.box, f.box) + (f.label === it.label ? 0.3 : 0); if (s > bi) { bi = s; best = j; } });
      if (best >= 0) { used.add(best); const f = fresh[best]; it.box = it.box.map((v, k) => v * 0.4 + f.box[k] * 0.6); it.label = f.label; it.confidence = f.confidence; it.miss = 0; }
      else it.miss += 1;
    });
    lensOv.items = lensOv.items.filter(it => it.miss < 3).concat(fresh.filter((_, j) => !used.has(j)).map(f => ({ ...f, miss: 0, born: now })));
  }
  lensOv.born = performance.now();
  lensOv.status = status || "";
}

function lensOverlayShift(dx, dy) { lensOv.dx = dx; lensOv.dy = dy; }

function lensBracket(g, x, y, w, h, color, k) {
  const L = Math.min(18, w / 3, h / 3) * k;
  g.strokeStyle = color; g.lineWidth = 2; g.shadowColor = color; g.shadowBlur = 12;
  g.beginPath();
  [[x, y, 1, 1], [x + w, y, -1, 1], [x, y + h, 1, -1], [x + w, y + h, -1, -1]].forEach(([px, py, sx, sy]) => {
    g.moveTo(px + sx * L, py); g.lineTo(px, py); g.lineTo(px, py + sy * L);
  });
  g.stroke();
}

function lensDraw(t) {
  const c = lensOv.canvas;
  if (!c || !c.width) return;
  const g = c.getContext("2d"), W = c.width, H = c.height;
  g.clearRect(0, 0, W, H);
  g.save();
  // scan line
  lensOv.sweep = (t / 2400) % 1;
  const y = lensOv.sweep * H, grad = g.createLinearGradient(0, y - 40, 0, y + 2);
  grad.addColorStop(0, "rgba(0,240,255,0)"); grad.addColorStop(1, "rgba(0,240,255,0.35)");
  g.fillStyle = grad; g.fillRect(0, y - 40, W, 42);
  g.fillStyle = "rgba(0,240,255,0.9)"; g.fillRect(0, y, W, 1);
  // faint grid
  g.strokeStyle = "rgba(0,240,255,0.06)"; g.lineWidth = 1;
  for (let x = 0; x < W; x += 40) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H); g.stroke(); }
  // findings: brackets grow in (lock-on), labels typed out
  g.font = "12px ui-monospace, Menlo, monospace";
  lensOv.items.forEach((f, i) => {
    const age = (t - (f.born || lensOv.born)) / 450, k = Math.min(1, Math.max(0.15, age));
    const s = lensOv.scale, col = LENS_COLORS[f.kind] || "#00f0ff";
    const [bx, by, bw, bh] = [(f.box[0] + lensOv.dx) * s, (f.box[1] + lensOv.dy) * s, f.box[2] * s, f.box[3] * s];
    g.globalAlpha = f.miss ? Math.max(0.25, 1 - f.miss * 0.3) : 1;
    const grow = 1 + (1 - k) * 0.6, cx = bx + bw / 2, cy = by + bh / 2;
    lensBracket(g, cx - bw * grow / 2, cy - bh * grow / 2, bw * grow, bh * grow, col, k);
    if (k > 0.6) {
      const conf = f.confidence != null ? ` ${Math.round(f.confidence * 100)}%` : "";
      const txt = (f.label || "").slice(0, Math.floor(40 * Math.min(1, (age - 0.6) * 2)));
      const label = `${txt}${txt.length === (f.label || "").length ? conf : "▌"}`;
      const tw = g.measureText(label).width + 8;
      g.shadowBlur = 0; g.fillStyle = "rgba(7,6,15,0.82)"; g.fillRect(bx, Math.max(0, by - 17), tw, 15);
      g.fillStyle = col; g.fillText(label, bx + 4, Math.max(11, by - 6));
    }
    g.globalAlpha = 1;
  });
  // status corner
  g.shadowBlur = 0; g.fillStyle = "rgba(255,42,109,0.9)";
  g.fillText(`// ${lensOv.status}`.toUpperCase(), 10, H - 10);
  g.restore();
}
