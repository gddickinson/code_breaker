/* Illustrations for every step of the Learn to Solve guides, drawn as SVG. */
const PAL = { w: "#f4f4f0", y: "#f5d800", g: "#17b45a", b: "#2b6cf0", r: "#e0263a", o: "#ff7a14", ".": "#3a3560" };
const svg = (w, h, body, label) => `<svg class="gd" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img" aria-label="${label || "Illustration"}">${body}</svg>`;
const txt = (x, y, s, cls = "gdt", anchor = "middle") => `<text x="${x}" y="${y}" class="${cls}" text-anchor="${anchor}">${s}</text>`;

/* Isometric cube: top, front and right faces, each a nine-letter colour string. */
function isoCube(top, front, right, label) {
  const S = 26, ox = 110, oy = 12;
  const pt = (a, b, c) => [ox + (a - b) * S * 0.87, oy + (a + b) * S * 0.5 + c * S];
  const quad = (p, fill) => `<polygon points="${p.map(q => q.map(v => v.toFixed(1)).join(",")).join(" ")}" fill="${fill}" stroke="#0d0b1e" stroke-width="2.5" stroke-linejoin="round"/>`;
  let body = "";
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) {
    body += quad([pt(c, r, 0), pt(c + 1, r, 0), pt(c + 1, r + 1, 0), pt(c, r + 1, 0)], PAL[top[r * 3 + c]]);
    body += quad([pt(c, 3, r), pt(c + 1, 3, r), pt(c + 1, 3, r + 1), pt(c, 3, r + 1)], PAL[front[r * 3 + c]]);
    body += quad([pt(3, 3 - c, r), pt(3, 2 - c, r), pt(3, 2 - c, r + 1), pt(3, 3 - c, r + 1)], PAL[right[r * 3 + c]]);
  }
  return svg(220, 190, body, label);
}

function grid(n, size, cell, label, extra = "") {
  let b = "";
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) b += cell(r, c, c * size + 2, r * size + 2, size);
  return svg(n * size + 4, n * size + 4, b + extra, label);
}

function sudoku(cells, label, extra = "") {
  const S = 22;
  let lines = "";
  for (let i = 0; i <= 9; i += 3) lines += `<line x1="${i * S + 2}" y1="2" x2="${i * S + 2}" y2="${9 * S + 2}" class="gdb"/><line y1="${i * S + 2}" x1="2" y2="${i * S + 2}" x2="${9 * S + 2}" class="gdb"/>`;
  return grid(9, S, (r, c, x, y) => {
    const v = cells[`${r},${c}`] || {};
    return `<rect x="${x}" y="${y}" width="${S}" height="${S}" class="gdc ${v.k || ""}"/>${v.t ? txt(x + S / 2, y + 16, v.t, v.small ? "gds" : "gdn") : ""}`;
  }, label, lines + extra);
}
const sc = (list, k, t) => Object.fromEntries(list.map(([r, c, s]) => [`${r},${c}`, { k, t: s ?? t }]));

function lightsBoard(g, marks = [], label) {
  return grid(5, 26, (r, c, x, y, S) => { const i = r * 5 + c; return `<rect x="${x + 1}" y="${y + 1}" width="${S - 2}" height="${S - 2}" rx="4" fill="${g[i] ? "var(--yellow)" : "#1b1638"}" stroke="${marks.includes(i) ? "var(--pink)" : "none"}" stroke-width="3"/>`; }, label);
}
const row = (...items) => `<div class="gdrow">${items.join("")}</div>`;
const arrow = () => `<span class="gdarrow" aria-hidden="true">→</span>`;
const cap = (s, html) => `<figure class="gdf">${html}<figcaption>${s}</figcaption></figure>`;
function chase(g) { let x = [...g]; const marks = []; for (let y = 1; y < 5; y++) for (let c = 0; c < 5; c++) if (x[(y - 1) * 5 + c]) { marks.push(y * 5 + c); x = lightsApply(x, 5, y * 5 + c); } return [x, marks]; }

const tiles = (s, label) => grid(3, 40, (r, c, x, y, S) => { const v = s[r * 3 + c]; return v ? `<rect x="${x + 2}" y="${y + 2}" width="${S - 4}" height="${S - 4}" rx="5" fill="var(--c1)"/>${txt(x + S / 2, y + 27, v, "gdn")}` : ""; }, label);
function hanoiPic(pegs, label) { let b = ""; pegs.forEach((p, i) => { const cx = 42 + i * 80; b += `<rect x="${cx - 2}" y="22" width="4" height="76" fill="#5b52a0"/>`; p.forEach((d, h) => { const w = 14 + d * 12; b += `<rect x="${cx - w / 2}" y="${84 - h * 14}" width="${w}" height="12" rx="3" fill="var(--pink)"/>`; }); }); return svg(244, 104, b + '<rect x="4" y="97" width="236" height="3" fill="var(--accent)"/>', label); }
function chessPic(n, S, mark, label, extra = "") { return grid(n, S, (r, c, x, y, s) => `<rect x="${x}" y="${y}" width="${s}" height="${s}" fill="${(r + c) % 2 ? "#2a2358" : "#151232"}"/>${mark(r, c, x, y, s) || ""}`, label, extra); }
const qn = (x, y, s) => `<text x="${x + s / 2}" y="${y + s * 0.74}" text-anchor="middle" font-size="${s * 0.68}" fill="var(--yellow)">♛</text>`;
const lineCells = (arr, S = 22, label) => svg(arr.length * S + 4, S + 4, arr.map((v, i) => `<rect x="${i * S + 2}" y="2" width="${S}" height="${S}" fill="${v === 2 ? "var(--pink)" : v === 1 ? "var(--c1)" : "#151232"}" stroke="#3a3560"/>${v === 3 ? txt(i * S + 13, 19, "·", "gdn") : ""}`).join(""), label);
const pegs = (a, label) => svg(a.length * 28 + 4, 30, a.map((v, i) => `<circle cx="${i * 28 + 16}" cy="15" r="11" fill="${PAL[v]}"/>`).join(""), label);

const G = "ggggggggg", W = "wwwwwwwww";
function diagramsFor() {
  const board = Array(25).fill(0); [1, 2, 6, 8, 12].forEach(i => { board[i] = 1; });
  const [afterChase, marks] = chase(board);
  const bottom = Array(25).fill(0); [20, 24].forEach(i => { bottom[i] = 1; });
  let pressed = [...bottom]; [0, 1].forEach(i => { pressed = lightsApply(pressed, 5, i); });
  const cleared = chase(pressed)[0];
  return {
    cube: [
      cap("A white plus sign, with each edge matching its side centre", isoCube(".w.www.w.", ".g..g....", ".r..r....", "White cross on top")),
      cap("All of the white layer is complete", isoCube(W, "ggg.g....", "rrr.r....", "White face and top row of each side complete")),
      cap("Now yellow side up: the middle layer is done", isoCube("....y....", "...gggggg", "...oooooo", "Two lower layers solved with yellow centre on top")),
      row(cap("Dot", isoCube("....y....", "...gggggg", "...oooooo", "Yellow dot")), arrow(), cap("L shape", isoCube(".y.yy....", "...gggggg", "...oooooo", "Yellow L")), arrow(), cap("Line", isoCube("...yyy...", "...gggggg", "...oooooo", "Yellow line")), arrow(), cap("Cross", isoCube(".y.yyy.y.", "...gggggg", "...oooooo", "Yellow cross"))),
      cap("The yellow edges match their side centres", isoCube(".y.yyy.y.", ".g.gggggg", ".o.oooooo", "Yellow edges aligned with sides")),
      cap("Corners in their correct spots, perhaps still twisted", isoCube("gygyyyoyo", "rgygggggg", "bobooooo".padEnd(9, "o"), "Yellow corners placed but not all oriented")),
      cap("Finished: every face is one colour", isoCube("yyyyyyyyy", G, "ooooooooo", "Solved cube")),
    ],
    sudoku: [
      cap("Fives elsewhere block this box until only one cell is left", sudoku({ ...sc([[0, 5], [1, 7], [5, 0], [7, 1]], "gdh", "5"), ...sc([[0, 0], [0, 1], [0, 2], [1, 0], [1, 1], [1, 2], [2, 0], [2, 1]], "gdx"), ...sc([[2, 2]], "gdt2", "5") }, "Hidden single")),
      cap("The row, column and box rule out all but 9", sudoku({ ...sc([[4, 0], [4, 2], [4, 7]], "", null), "4,0": { t: "1" }, "4,2": { t: "2" }, "4,7": { t: "3" }, "0,4": { t: "4" }, "2,4": { t: "5" }, "7,4": { t: "6" }, "3,3": { t: "7" }, "5,5": { t: "8" }, "4,4": { k: "gdt2", t: "9" } }, "Naked single")),
      cap("Small candidate digits in each empty cell", sudoku({ "0,0": { t: "1 4 7", small: 1 }, "0,1": { t: "2 7", small: 1 }, "0,2": { t: "5", k: "" }, "1,0": { t: "1 7", small: 1 }, "1,1": { t: "3 9", small: 1 }, "1,2": { t: "2 9", small: 1 } }, "Pencil marks")),
      cap("Cells holding only 2 and 7 claim those digits, so remove them nearby", sudoku({ "3,1": { k: "gdh", t: "2 7", small: 1 }, "3,5": { k: "gdh", t: "2 7", small: 1 }, "3,3": { k: "gdx", t: "1 2", small: 1 }, "3,7": { k: "gdx", t: "4 7", small: 1 } }, "Naked pair")),
      cap("Within this box a 4 must be in this row, so remove 4 further along", sudoku({ "1,3": { k: "gdh", t: "4", small: 1 }, "1,4": { k: "gdh", t: "4", small: 1 }, "1,7": { k: "gdx", t: "4", small: 1 } }, "Pointing candidates")),
      cap("A rectangle of candidates clears both columns", sudoku({ ...sc([[1, 2], [1, 7], [6, 2], [6, 7]], "gdh", "6"), ...sc([[3, 2], [4, 7]], "gdx", "6") }, "X-wing", `<rect x="${2 * 22 + 13}" y="${1 * 22 + 13}" width="${5 * 22}" height="${5 * 22}" fill="none" stroke="var(--pink)" stroke-width="2"/>`)),
    ],
    lights: [
      row(cap("Press below each lit cell (pink)", lightsBoard(board, marks, "Lit board with chase presses")), arrow(), cap("Only the bottom row stays lit", lightsBoard(afterChase, [], "After chasing"))),
      cap("This board's bottom row is 10001", lightsBoard(bottom, [], "Bottom row lit at both ends")),
      cap("The table says press 11000 on the top row", lightsBoard(bottom, [0, 1], "Top row presses")),
      row(cap("After the top-row presses", lightsBoard(pressed, [], "After top-row presses")), arrow(), cap("Chase again: all dark", lightsBoard(cleared, [], "Empty board"))),
    ],
    mastermind: [
      cap("Open with two pairs", pegs(["r", "r", "b", "b"], "Two pairs")),
      cap("Add the pegs: 3 of these 4 are in the code", row(pegs(["r", "r", "b", "b"], "Guess"), `<span class="gdfb">● ● ○</span>`)),
      cap("Every guess must fit all earlier feedback", row(pegs(["r", "b", "r", "g"], "Next guess"), `<span class="gdfb">Still possible</span>`)),
      cap("Change only part of the code", row(pegs(["r", "b", "r", "g"], "Before"), arrow(), pegs(["r", "b", "y", "g"], "After"))),
    ],
    sliding: [
      cap("Top row placed", tiles([1, 2, 3, 6, 4, 0, 7, 5, 8], "Top row complete")),
      cap("Left column placed too", tiles([1, 2, 3, 4, 6, 0, 7, 5, 8], "Top row and left column complete")),
      row(cap("Rotate the last 2×2", tiles([1, 2, 3, 4, 6, 0, 7, 5, 8], "Remaining block")), arrow(), cap("Solved", tiles([1, 2, 3, 4, 5, 6, 7, 8, 0], "Solved tiles"))),
    ],
    hanoi: [
      row(cap("Start: four discs", hanoiPic([[4, 3, 2, 1], [], []], "Four discs on first peg")), arrow(), cap("Smallest moves first", hanoiPic([[4, 3, 2], [1], []], "Smallest moved"))),
      row(cap("The only other legal move", hanoiPic([[4, 3], [1], [2]], "Second disc moves")), arrow(), cap("Smallest moves again", hanoiPic([[4, 3], [], [2, 1]], "Smallest moves onto second disc"))),
      row(cap("Top three moved out of the way", hanoiPic([[4], [3, 2, 1], []], "Three discs moved")), arrow(), cap("Move the largest", hanoiPic([[], [3, 2, 1], [4]], "Largest moved")), arrow(), cap("Bring the three back", hanoiPic([[], [], [4, 3, 2, 1]], "Finished"))),
    ],
    queens: [
      cap("One queen in each row, in the first safe column", chessPic(6, 26, (r, c, x, y, s) => ([[0, 1], [1, 3]].some(q => q[0] === r && q[1] === c) ? qn(x, y, s) : ""), "Two queens placed")),
      cap("Red shows every square a queen attacks", chessPic(6, 26, (r, c, x, y, s) => (r === 1 && c === 3 ? qn(x, y, s) : (r === 1 || c === 3 || Math.abs(r - 1) === Math.abs(c - 3)) ? `<rect x="${x}" y="${y}" width="${s}" height="${s}" fill="var(--pink)" opacity=".45"/>` : ""), "Queen attacks")),
      cap("No safe square in this row, so go back and move the queen above", chessPic(4, 34, (r, c, x, y, s) => ([[0, 0], [1, 2]].some(q => q[0] === r && q[1] === c) ? qn(x, y, s) : r === 2 ? `<rect x="${x}" y="${y}" width="${s}" height="${s}" fill="var(--pink)" opacity=".45"/>` : ""), "Dead end in the third row")),
    ],
    knight: [
      cap("Numbers count onward moves: choose the smallest", chessPic(5, 34, (r, c, x, y, s) => { const opts = { "1,2": 3, "0,1": 2 }[`${r},${c}`]; if (r === 2 && c === 0) return txt(x + s / 2, y + 24, "♞", "gdn"); return opts !== undefined ? txt(x + s / 2, y + 23, opts, "gdn") : ""; }, "Knight choosing move")),
      cap("Corners have only two entrances, so use them early", chessPic(5, 34, (r, c, x, y, s) => { if (r === 0 && c === 0) return `<rect x="${x + 3}" y="${y + 3}" width="${s - 6}" height="${s - 6}" fill="none" stroke="var(--pink)" stroke-width="3"/>`; return (r === 1 && c === 2) || (r === 2 && c === 1) ? txt(x + s / 2, y + 24, "♞", "gdn") : ""; }, "Corner square and its two entrances")),
    ],
    nonogram: [
      cap("Clue 7 in 10 cells: slide left, slide right, keep the overlap", `<div class="gdcol">${lineCells([1, 1, 1, 1, 1, 1, 1, 0, 0, 0], 22, "Run pushed left")}${lineCells([0, 0, 0, 1, 1, 1, 1, 1, 1, 1], 22, "Run pushed right")}${lineCells([0, 0, 0, 2, 2, 2, 2, 0, 0, 0], 22, "Overlap")}</div>`),
      cap("Clue is complete: mark the remaining cells blank", lineCells([3, 3, 1, 1, 1, 3, 3, 3, 3, 3], 22, "Blanks marked")),
      cap("A filled cell at the edge starts the run: clue 4 is forced", lineCells([2, 1, 1, 1, 3, 0, 0, 0, 0, 0], 22, "Run from edge")),
      cap("A mark in a row helps its column", lineCells([0, 1, 1, 0, 2, 0, 1, 0, 0, 0], 22, "Line with new mark")),
    ],
    cipher: [
      cap("Count letters: the tallest bars are probably E, T, A", svg(240, 74, [38, 28, 22, 18, 14, 10, 7, 4].map((h, i) => `<rect x="${i * 28 + 8}" y="${62 - h}" width="20" height="${h}" fill="${i < 3 ? "var(--pink)" : "var(--c1)"}" rx="3"/>${txt(i * 28 + 18, 73, "XQHBTAZK"[i])}`).join(""), "Letter frequency bars")),
      cap("A one-letter word is A or I, and QGW may be THE", `<div class="gdcode"><b>Q</b> QGW → <em>A</em> THE</div>`),
      cap("Letter patterns give away words", `<div class="gdcode">X Y Z Z Y X → <em>pattern 1 2 3 3 2 1</em></div>`),
      cap("Pencil in guesses above the ciphertext", `<div class="gdcode"><em>T H E</em> &nbsp; <em>· · T</em><br>Q G W &nbsp; M R Q</div>`),
      cap("When every word reads, you are done", `<div class="gdcode"><em>THE ANSWER IS IN THE GARDEN</em></div>`),
    ],
  };
}
if (typeof module !== "undefined") module.exports = { diagramsFor };
