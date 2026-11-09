/* How secrets have been hidden and transmitted, with a working image-steganography demo. */
route(/^\/channels$/, async () => {
  const data = (await (await fetch("/static/channels.json")).json()).sort((a, b) => a.sort - b.sort);
  const row = e => `<li><div class="ch"><time>${esc(e.year)}</time><b>${esc(e.title)}</b><span>${esc(e.text)}</span><small>${esc(e.use)}</small>${e.link ? `<a href="${esc(e.link[1])}">${esc(e.link[0])} →</a>` : ""}${e.demo ? '<a href="#demo" id="jump">Try it below ↓</a>' : ""}</div></li>`;
  const col = k => `<section><h2>${k === "Hiding" ? "Hiding that a message exists" : "Moving messages over distance"}</h2><ol class="timeline slim">${data.filter(e => e.kind === k).map(row).join("")}</ol></section>`;
  view().innerHTML = `<p class="kicker">// CHANNELS</p><h1>How secrets travel</h1><p class="lead">A cipher hides what a message says. Steganography hides that there is a message at all. And every message has to get across somehow, with each new channel changing what codebreakers could intercept.</p>
    <div class="two channels">${col("Hiding")}${col("Transmission")}</div>
    <h2 id="demo">Hide a message in a picture</h2><div class="panel"><p>Each colour value changes by at most 1 out of 255, too little to see. The right-hand panel exaggerates only the low bits, which is where the message shows up.</p>
    <label for="m">Secret message</label><input id="m" value="Meet me at the old lighthouse at dawn." maxlength="1500">
    <div class="three">${[["a", "Original"], ["b", "With hidden message"], ["c", "Low bits, enhanced"]].map(([i, l]) => `<figure><canvas id="${i}" width="200" height="200" role="img" aria-label="${l}"></canvas><figcaption>${l}</figcaption></figure>`).join("")}</div>
    <h3>Read back from the picture's pixels</h3><pre id="o"></pre><p id="n" class="mute"></p></div>`;
  const size = 200, src = $("#a").getContext("2d"), grad = src.createLinearGradient(0, 0, size, size);
  grad.addColorStop(0, "#22306e"); grad.addColorStop(1, "#b0406e"); src.fillStyle = grad; src.fillRect(0, 0, size, size);
  src.fillStyle = "#f5e642"; src.beginPath(); src.arc(140, 62, 30, 0, 7); src.fill(); src.fillStyle = "#0d1830"; src.beginPath(); src.moveTo(0, 170); src.lineTo(70, 90); src.lineTo(130, 150); src.lineTo(165, 112); src.lineTo(200, 160); src.lineTo(200, 200); src.lineTo(0, 200); src.fill();
  const base = src.getImageData(0, 0, size, size), rgb = new Uint8Array(size * size * 3);
  for (let i = 0, j = 0; i < base.data.length; i += 4) { rgb[j++] = base.data[i]; rgb[j++] = base.data[i + 1]; rgb[j++] = base.data[i + 2]; }
  const put = (id, f) => { const g = $("#" + id).getContext("2d"), im = g.createImageData(size, size); for (let i = 0, j = 0; i < im.data.length; i += 4) { im.data[i] = f(j++); im.data[i + 1] = f(j++); im.data[i + 2] = f(j++); im.data[i + 3] = 255; } g.putImageData(im, 0, 0); };
  const draw = () => {
    const out = lsbEmbed(rgb, $("#m").value);
    put("b", j => out[j]); put("c", j => (out[j] & 1) * 255);
    let changed = 0; out.forEach((v, i) => { if (v !== rgb[i]) changed++; });
    $("#o").textContent = lsbExtract(out); $("#n").textContent = `${changed} colour values changed, each by 1, out of ${rgb.length.toLocaleString()}.`;
  };
  $("#m").oninput = draw; draw();
  $("#jump").onclick = e => { e.preventDefault(); $("#demo").scrollIntoView({ behavior: "smooth" }); };
}, "channels");
