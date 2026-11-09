/* Recovering information: scans, image reconstruction and data wrangling, with measured results. */
const REC_PCT = v => `${(v * 100).toFixed(0)}%`;
const REC_IMG = "/static/recovery/";
const REC_ADS = [
  ["1 Jul 1882, writer 5", "Readable", "Table 2217 gives: Aime moi un peu, je t'aime et desire tant te baiser.", "The OCR was right. Word-break repair garbled the display, not the decrypt."],
  ["13 Nov 1884, writer 78", "Readable", "Caesar shift of 2 gives: Je t'adore. Te voir est mon seul bonheur.", "OCR dropped a word containing an apostrophe, and the full reading needed the scan."],
  ["20 Sep 1894, writer 25", "Readable after repair", "Vigenere CD without W gives: Espere diner avec toi ou serai tres peinee.", "A damaged h and an fl ligature were misread. Both errors sat inside words that nearly read."],
  ["18 Sep 1896, writer 23", "Partly read", "Every second letter contains UNIQUEMENT. The other stream is not read.", "The machine reading was a fragment, and the transposition is not understood."],
  ["9 Jan 1884, writer N", "Unread", "The flagged text was a quarter of the ad. A solver on the full text did no better than shuffles.", "Every word containing a digit had been discarded before decryption."],
  ["2 Sep 1881, AMI", "Rejected", "Abbreviated French with initials, not an enciphered text.", "OCR kept only the longer pieces, which happened to make French words."],
  ["6 Feb 1890, Severe", "Rejected", "Abbreviated plain French: Voys auc. mal! and a row of initials.", "Reversing word order on plain words proves nothing."],
];
const REC_FAMOUS = [
  ["Archimedes Palimpsest", "Multispectral imaging separated a 10th-century copy of Archimedes from the prayer book written over it, because the two inks respond differently across wavelengths."],
  ["En-Gedi scroll", "A burnt scroll that could not be opened was read by X-ray micro-CT and virtual unwrapping: find the surface in 3D, flatten it, then render the ink. It proved to be Leviticus."],
  ["Herculaneum papyri", "The Vesuvius Challenge trained machine learning to spot carbon ink in CT scans of carbonised scrolls, and the first word was read in 2023."],
  ["Stasi files", "East German secret police tore files by hand in 1989. Investigators have rebuilt pages by hand, and Fraunhofer developed scanning and matching software to speed it up."],
  ["DARPA Shredder Challenge", "In 2011, teams reassembled shredded documents from images, using edge shape, ink continuity and language."],
];
const REC_STEPS = [
  ["Keep the original", "Never overwrite a source. Each processed version should be reproducible from the scan by code."],
  ["Look before you measure", "View a sample of images early. Abbreviated French and digit-laden ciphers were invisible in the summary numbers."],
  ["Build ground truth", "Transcribe a sample by eye, and score every method on it. Choosing by what looks clean is unreliable."],
  ["Count what you discard", "Each filter should report what it removed. A silent filter can remove the signal."],
  ["Keep uncertainty", "Record alternatives for doubtful glyphs. Two people's transcriptions, or two engines, show where the text is unstable."],
  ["Use the cipher as a check", "A correct key makes nearby errors stand out. Repair only with a control on clean text."],
  ["Return to the image", "Check every reading against the scan before believing it."],
];

function recChart(s) {
  const W = 640, H = 300, L = 54, R = 130, T = 16, B = 44, n = s.rates.length, names = Object.keys(s.series), cols = ["--c1", "--c2", "--c3"];
  const x = i => L + i * (W - L - R) / (n - 1), y = v => T + (1 - v) * (H - T - B);
  const grid = [0, .25, .5, .75, 1].map(v => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${L - 8}" y="${y(v) + 4}" text-anchor="end" fill="var(--mute)" font-size="12">${REC_PCT(v)}</text>`).join("");
  const xs = s.rates.map((r, i) => `<text x="${x(i)}" y="${H - B + 18}" text-anchor="middle" fill="var(--mute)" font-size="12">${REC_PCT(r)}</text>`).join("");
  const lines = names.map((k, j) => `<polyline fill="none" stroke="var(${cols[j]})" stroke-width="2" points="${s.series[k].map((v, i) => `${x(i)},${y(v)}`).join(" ")}"/>` + s.series[k].map((v, i) => `<circle cx="${x(i)}" cy="${y(v)}" r="4.5" fill="var(${cols[j]})" stroke="var(--panel)" stroke-width="2"><title>${esc(k)}: ${REC_PCT(s.rates[i])} damaged, ${REC_PCT(v)} of the plaintext recovered</title></circle>`).join("")).join("");
  const ends = names.map(k => ({ k, v: s.series[k][n - 1] })).sort((a, b) => b.v - a.v);
  let last = -99; const labels = ends.map(e => { const py = Math.max(y(e.v) + 4, last + 16); last = py; return `<text x="${W - R + 8}" y="${py}" fill="var(--ink)" font-size="12">${esc(e.k)}</text>`; }).join("");
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Plaintext recovered as ciphertext damage increases" style="width:100%;max-width:760px">${grid}${xs}${lines}${labels}<text x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle" fill="var(--mute)" font-size="12">Share of ciphertext letters damaged</text></svg>
  <div class="legend">${names.map((k, j) => `<span><i style="display:inline-block;width:12px;height:12px;background:var(${cols[j]});margin:0 6px 0 14px"></i>${esc(k)}</span>`).join("")}</div>`;
}

function recBars(rows) {
  return rows.map(r => `<div style="display:grid;grid-template-columns:minmax(120px,190px) 1fr 48px;gap:10px;align-items:center;margin:6px 0"><span>${esc(r.stage)}</span><div style="background:rgba(255,255,255,.05);height:14px;border-radius:0 4px 4px 0"><div title="${esc(r.stage)}: ${REC_PCT(r.recovered)}" style="width:${r.recovered * 100}%;height:14px;background:var(--c1);border-radius:0 4px 4px 0"></div></div><b>${REC_PCT(r.recovered)}</b></div>`).join("");
}

function recOtsu(hist, total) {
  let sum = 0, sumB = 0, wB = 0, best = 0, at = 127;
  hist.forEach((c, i) => { sum += i * c; });
  for (let t = 0; t < 256; t++) { wB += hist[t]; if (!wB || wB === total) continue; sumB += t * hist[t]; const mB = sumB / wB, mF = (sum - sumB) / (total - wB), v = wB * (total - wB) * (mB - mF) ** 2; if (v > best) { best = v; at = t; } }
  return at;
}

function recThreshold() {
  const cv = $("#recCanvas"), s = $("#recT"), img = new Image();
  if (!cv) return;
  img.onload = () => {
    cv.width = img.width; cv.height = img.height;
    const c = cv.getContext("2d"); c.drawImage(img, 0, 0);
    const src = c.getImageData(0, 0, cv.width, cv.height), g = new Uint8Array(cv.width * cv.height), hist = new Array(256).fill(0);
    for (let i = 0; i < g.length; i++) { g[i] = Math.round(.299 * src.data[i * 4] + .587 * src.data[i * 4 + 1] + .114 * src.data[i * 4 + 2]); hist[g[i]]++; }
    const otsu = recOtsu(hist, g.length);
    const draw = () => { const t = +s.value, o = c.createImageData(cv.width, cv.height); for (let i = 0; i < g.length; i++) { const v = g[i] > t ? 255 : 0; o.data[i * 4] = o.data[i * 4 + 1] = o.data[i * 4 + 2] = v; o.data[i * 4 + 3] = 255; } c.putImageData(o, 0, 0); $("#recTv").textContent = `Threshold ${t}. Otsu's method picks ${otsu}.`; };
    s.oninput = draw; $("#recO").onclick = () => { s.value = otsu; draw(); }; s.value = otsu; draw();
  };
  img.src = `${REC_IMG}ad25_scan.png`;
}

route(/^\/recovery$/, async () => {
  const d = await (await fetch(`${REC_IMG}results.json`)).json(), o = d.ocr, best = o.table[0], rc = d.repair_control, rr = d.repair_real, rec = d.reconstruction, dg = d.digits;
  const fig = (f, c) => `<figure style="margin:8px 0"><img src="${REC_IMG}${f}" alt="${esc(c)}" style="max-width:100%;background:#fff;display:block"><figcaption class="mute">${esc(c)}</figcaption></figure>`;
  const sample = o.samples["1894_18940920-25.jpg"] || [];
  view().innerHTML = `<p class="kicker">// RECOVERY</p><h1>Recovering the message</h1>
  <p class="lead">A cipher can only be attacked once it has become reliable data. Real sources are stained, torn, faded or badly scanned, and each error passes straight into the analysis.</p>
  <section class="panel"><h2>A real example: seven Le Figaro ads</h2><p>The automatic search flagged seven more ads from 1881 to 1896. Each was then checked against its scan.</p>
  <div style="overflow-x:auto"><table><thead><tr><th>Ad</th><th>Outcome</th><th>Reading</th><th>What the scan showed</th></tr></thead><tbody>${REC_ADS.map(r => `<tr>${r.map(c => `<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
  <p>These are candidate readings. They have not been checked against the database maintainer's own solutions.</p></section>
  <h2>1. Clean up the image</h2><p>Scanned newsprint has grey paper, show-through and specks. Thresholding converts it to pure black and white, and the choice of cut-off matters. Otsu's method chooses the value that best separates the two groups of pixels.</p>
  <div class="panel"><h3>Try it on the 1894 ad</h3><canvas id="recCanvas" style="max-width:100%;background:#fff"></canvas><div class="row" style="align-items:center"><input id="recT" type="range" min="0" max="255" aria-label="Threshold" style="flex:1"><button id="recO" class="cta">Use Otsu</button></div><p id="recTv" class="reading"></p></div>
  <div class="biogrid"><div class="panel">${fig("adn_scan.png", "Original scan")}</div><div class="panel">${fig("adn_otsu.png", "Otsu threshold")}</div><div class="panel">${fig("adn_adaptive.png", "Adaptive threshold")}</div><div class="panel">${fig("adn_denoise.png", "Non-local means denoising")}</div></div>
  <h2>2. Rebuild a damaged image</h2><p>To measure reconstruction you need to know the answer, so these ${rec.lines} test lines were rendered from random letters, damaged in a known way, then restored one stage at a time. Random letters leave no language to lean on. Tesseract recovers ${REC_PCT(rec.clean)} of the undamaged lines.</p>
  <div class="panel">${recBars(rec.stages)}</div><div class="panel">${rec.stages.map((s, i) => fig(`stage${i}.png`, s.stage)).join("")}</div>
  <p>Flattening divides out uneven paper. Straightening finds the rotation that lines ink up into rows. Wiener filtering reverses a blur, and a damping term stops it from amplifying noise. Each stage only counts if the score rises, and a step that looks better can still make reading worse.</p>
  <h2>3. Compare OCR methods on known answers</h2><p>Scored on ${o.ads} ads whose text was transcribed by eye. That is a small sample, so close results are ties. Best mean: ${esc(best.engine)} on ${esc(best.variant)}, recovering ${REC_PCT(best.mean)} of characters.</p>
  <div class="panel" style="overflow-x:auto"><table><thead><tr><th>Cleanup</th><th>Engine</th><th>Mean recovered</th><th>Worst ad</th></tr></thead><tbody>${o.table.map(r => `<tr><td>${esc(r.variant)}</td><td>${esc(r.engine)}</td><td>${REC_PCT(r.mean)}</td><td>${REC_PCT(r.worst)}</td></tr>`).join("")}</tbody></table></div>
  <div class="panel"><h3>One line, several readings</h3>${fig("ad25_scan.png", "1894 ad, original scan")}<table><tbody>${sample.map(x => `<tr><td>${esc(x.variant)}</td><td>${esc(x.engine)}</td><td class="reading">${esc(x.text)}</td><td>${REC_PCT(x.recovered)}</td></tr>`).join("")}</tbody></table></div>
  <h2>4. Wrangle the text</h2><div class="biogrid"><div class="panel"><h3>Period typography</h3><p>Ligatures such as fi and fl, the long s, drop capitals and worn type all produce characters that a modern model has not been trained on.</p></div><div class="panel"><h3>Mixed symbols</h3><p>Filtering out tokens with digits removed the body of the N ad. ${dg.letter_digit_ads} of ${dg.ads_read} ads read by OCR have three or more letter-digit tokens in one line. Some are OCR noise, and each one needs a look.</p></div><div class="panel"><h3>Layout</h3><p>Signatures, ad numbers, neighbouring ads and rules need separating from cipher text. Word breaks are evidence and should be retained.</p></div><div class="panel"><h3>Not everything is a cipher</h3><p>Abbreviated French looks strange, but it is not encrypted. Any decryption method can produce words from short fragments.</p></div></div>
  <h2>5. See how errors spread</h2><p>Each point averages ${d.spread.trials} French texts of ${d.spread.length} letters with the key known. A misread letter damages one plaintext letter. A dropped letter pushes a repeating key out of step for everything that follows.</p>
  <div class="panel">${recChart(d.spread)}</div>
  <h2>6. Let the key repair the text</h2><p>Once a key is known, each suspect letter can be swapped for the letters it is often confused with, and kept if the decrypt reads clearly better.</p>
  <div class="panel"><p><b>OCR gave</b></p><p class="reading">${esc(rr.ocr_plain)}</p><p><b>After repair</b></p><p class="reading">${esc(rr.plain)}</p><p>${rr.edits.map(e => `Position ${e.position}: ${esc(e.from)} became ${esc(e.to)}`).join("; ")}.</p></div>
  <p>Control: on ${rc.fragments} new French fragments of ${rc.length} letters, each with 2 planted errors, ${rc.fully_repaired} were fully repaired, and wrong letters went from ${rc.wrong_before} to ${rc.wrong_after}. On ${rc.fragments} clean fragments, ${rc.clean_changed} were wrongly edited. This requires a key that is already right.</p>
  <h2>Famous recoveries</h2><div class="biogrid">${REC_FAMOUS.map(([t, b]) => `<div class="panel"><h3>${esc(t)}</h3><p>${esc(b)}</p></div>`).join("")}</div>
  <h2>A working checklist</h2><ol>${REC_STEPS.map(([t, b]) => `<li><b>${esc(t)}.</b> ${esc(b)}</li>`).join("")}</ol>
  <div class="row"><a class="cta" href="#/mysteries">Mystery Lab</a><a class="cta" href="#/solutions">Candidate readings</a><a class="cta" href="#/theory">Theory</a></div>`;
  recThreshold();
}, "recovery");
