/* Hand-built SVG charts and the background cipher rain. All text is escaped. */
const CAT_COLORS = { cipher: "var(--c1)", script: "var(--c2)", "historic cipher": "var(--c3)" };

function heatmap(h) {
  const cell = v => v === null ? '<td style="background:#120f26" title="Not applicable">–</td>' : `<td title="${Math.round(v * 100)}% of letters recovered" style="background:rgba(0,160,181,${(0.1 + v * 0.8).toFixed(2)})">${Math.round(v * 100)}%</td>`;
  const marks = Object.entries(h.markers || {}).map(([k, [n, s]]) => `<li>${esc(k)}: ${n} symbols long, ${s} distinct</li>`).join("");
  return `<div class="scroll"><table class="heat"><thead><tr><th scope="col">${esc(h.row_label)} ↓ / ${esc(h.col_label)} →</th>${h.cols.map(c => `<th scope="col">${c}</th>`).join("")}</tr></thead><tbody>${h.rows.map((r, i) => `<tr><th scope="row">${r}</th>${h.values[i].map(cell).join("")}</tr>`).join("")}</tbody></table></div><h3>Where the famous ciphers sit</h3><ul>${marks}</ul>`;
}

function barChart(b) {
  const max = Math.max(...b.items.map(i => i.value), 1e-9), rowH = 22, w = 720, left = 150, h = 38 + b.items.length * rowH;
  const rows = b.items.map((it, i) => { const y = 32 + i * rowH, len = (w - left - 66) * it.value / max; return `<g><title>${esc(it.label)}: ${it.value} ${esc(b.unit || "")}</title><text x="${left - 8}" y="${y + 11}" text-anchor="end" class="axisl">${esc(it.label)}</text><rect x="${left}" y="${y}" width="${Math.max(len, 1)}" height="15" rx="3" fill="${it.hit ? "var(--c2)" : "var(--c1)"}"/><text x="${left + len + 6}" y="${y + 11}" class="axisl">${it.value}</text></g>`; }).join("");
  return `<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(b.title)}"><text x="12" y="20" class="charttitle">${esc(b.title)}</text>${rows}</svg>`;
}

/* Every code with data, placed by length and alphabet size on log scales. */
function codeMap(codes) {
  const pts = codes.filter(c => c.tokens > 0 && c.symbols > 0);
  const w = 900, h = 420, m = { l: 62, r: 20, t: 18, b: 44 };
  const X = v => m.l + (Math.log10(v) - 1) / 3.3 * (w - m.l - m.r), Y = v => h - m.b - Math.log10(v) / 2.6 * (h - m.t - m.b);
  const xt = [10, 30, 100, 300, 1000, 3000, 13000], yt = [2, 10, 30, 100, 300];
  const grid = xt.map(v => `<line x1="${X(v)}" x2="${X(v)}" y1="${m.t}" y2="${h - m.b}" stroke="var(--line)" stroke-width=".6"/><text x="${X(v)}" y="${h - m.b + 16}" text-anchor="middle" class="axisl">${v}</text>`).join("") + yt.map(v => `<line x1="${m.l}" x2="${w - m.r}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)" stroke-width=".6"/><text x="${m.l - 8}" y="${Y(v) + 4}" text-anchor="end" class="axisl">${v}</text>`).join("");
  const dots = pts.map(c => {
    const x = X(c.tokens), y = Y(Math.min(c.symbols, 390)), r = c.open_leads ? 8 : 5, fill = CAT_COLORS[c.category] || "var(--c4)";
    const tip = `<title>${esc(c.name)}: ${c.tokens} symbols, ${c.symbols} distinct, ${c.attempts} attempts, ${c.open_leads} open leads</title>`;
    const mark = c.category === "script" ? `<rect class="dot" x="${(x - r).toFixed(1)}" y="${(y - r).toFixed(1)}" width="${2 * r}" height="${2 * r}" rx="2" fill="${fill}" stroke="var(--panel)" stroke-width="2">${tip}</rect>` : `<circle class="dot" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r}" fill="${fill}" stroke="var(--panel)" stroke-width="2">${tip}</circle>`;
    return `<a href="#/lead/${esc(c.slug)}">${mark}</a>`;
  }).join("");
  return `<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Map of codes by length and alphabet size">${grid}${dots}<text x="${(w + m.l) / 2}" y="${h - 8}" text-anchor="middle" class="axisl">Message length (log scale)</text><text transform="rotate(-90 15 ${h / 2})" x="15" y="${h / 2}" text-anchor="middle" class="axisl">Distinct symbols (log scale)</text></svg>
    <div class="legend"><span><i style="background:var(--c1)"></i>Cipher</span><span><i style="background:var(--c2);border-radius:2px"></i>Lost script (square)</span><span>Larger dot: has open leads. Click a dot to open it.</span></div>`;
}

(function rain() {
  const c = document.getElementById("rain");
  if (!c || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const g = c.getContext("2d"), glyphs = "ᚠᚢᚦᚨᚱᚲ01ΑΒΓΔ☿♃⊕ABCDEFGHIJKLMNOPQRSTUVWXYZ𐇑".split(""), size = 16;
  let drops = [];
  const fit = () => { c.width = innerWidth; c.height = innerHeight; drops = Array(Math.ceil(c.width / size)).fill(0).map(() => Math.random() * c.height / size); };
  addEventListener("resize", fit); fit();
  setInterval(() => {
    if (document.hidden) return;
    g.fillStyle = "rgba(7,6,15,.12)"; g.fillRect(0, 0, c.width, c.height); g.font = `${size}px monospace`;
    drops.forEach((d, i) => { g.fillStyle = Math.random() < .05 ? "#ff2a6d" : "#00f0ff"; g.fillText(glyphs[Math.floor(Math.random() * glyphs.length)], i * size, d * size); drops[i] = d * size > c.height && Math.random() > .975 ? 0 : d + 1; });
  }, 70);
})();
