/* Sound Lab: birdsong and other sounds, as spectrograms, symbol sequences and identifications. */
const SND = { rec: null, chunks: [], stream: null };

function sndWav(samples, rate) {
  const buf = new ArrayBuffer(44 + samples.length * 2), v = new DataView(buf);
  const w = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  w(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); w(8, "WAVEfmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); w(36, "data"); v.setUint32(40, samples.length * 2, true);
  samples.forEach((s, i) => v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, s)) * 32767, true));
  return buf;
}

const sndB64 = buf => { let s = ""; const b = new Uint8Array(buf); for (let i = 0; i < b.length; i += 32768) s += String.fromCharCode(...b.subarray(i, i + 32768)); return btoa(s); };

function sndShow(r) {
  const st = r.stats || {}, b = r.birds || {}, y = r.sounds || {};
  const base = b.noise_baseline;
  $("#sndOut").innerHTML = `${r.source && r.source.url ? `<p class="mute">Recording: <a href="${esc(r.source.url)}" target="_blank" rel="noopener">${esc(r.source.title)}</a>, ${esc(r.source.license)}.</p>` : ""}
    <div class="panel"><h3>Spectrogram</h3><p class="mute">Time runs left to right and pitch rises upward, from 0 to ${(r.max_freq_hz / 1000).toFixed(0)} kHz over ${r.duration} s. The strip underneath marks each syllable with its type.</p><img src="${r.spectrogram}" alt="Spectrogram with syllables marked" style="width:100%;image-rendering:auto"></div>
    <div class="two"><div class="panel"><h3>The song as a code</h3>${r.sequence ? `<p class="reading" style="word-break:break-all">${esc(r.sequence)}</p>${table(["Syllables", "Types", "Entropy (bits)", "Most possible", "Given the previous syllable", "Repeats"], [[st.syllables, st.types, st.entropy_bits, st.max_bits, st.conditional_bits, `${Math.round(st.repeats * 100)}%`]])}
      <p class="mute">If knowing the last syllable lowers the uncertainty a lot, the song follows rules, like a language. Commonest transitions: ${(st.transitions || []).map(([p, n]) => `${esc(p)} (${n})`).join(", ")}.</p>${r.truth ? `<p><b>Control:</b> the true sequence was <span class="reading">${esc(r.truth)}</span>; the types found agree for ${Math.round((r.agreement || 0) * 100)}% of syllables, allowing any renaming.</p>` : ""}` : '<p class="mute">No clear syllables found between 1 and 10 kHz.</p>'}</div>
      <div class="panel"><h3>Which bird?</h3>${b.available ? (b.species.length ? `${table(["Species", "Scientific name", "Best confidence", "Windows"], b.species.map(s => [s.common, s.scientific, s.confidence, s.windows]))}<p class="mute">BirdNET, best 3-second window per species. ${base ? `Random noise scores up to ${base}.` : "Random noise produced no species."} Several species often score highly, so check the spectrogram and the location.</p>` : '<p class="mute">BirdNET found no species.</p>') : `<p class="err">BirdNET is not available: ${esc(b.error || "")}</p>`}
      <h3>What kind of sound?</h3>${y.available ? `${table(["Class", "Average", "Peak"], y.classes.map(c => [c.name, c.mean, c.peak]))}<p class="mute">YAMNet: 521 classes of everyday, natural and human sounds, averaged over ${y.frames} one-second frames.</p>` : `<p class="err">YAMNet is not available: ${esc(y.error || "")}</p>`}</div></div>`;
}

async function sndRun(body) {
  $("#sndMsg").textContent = "Analysing: spectrogram, syllables, BirdNET and YAMNet…";
  const r = await api("/sounds/analyse", body);
  $("#sndMsg").textContent = "";
  sndShow(r);
}


/* Pictures hidden in sound (Round 82): write text into a spectrogram, or look for one in any recording. */
function hiddenPanel() {
  return `<h2>Pictures hidden in sound</h2><div class="panel"><p>A spectrogram shows loudness over frequency and time, so a picture can be written into sound: each moment's frequencies set to one column of the picture. You hear a hiss or a chirp; the spectrogram shows the words. Measured on generated sound: words hidden in noise are read by OCR down to 0 dB and spotted by a structure test down to -10 dB; in birdsong OCR reads half of them at -15 dB; under a tone almost to -20 dB. Clean audio never produced a false word.</p>
    <div class="row"><div><label for="hdText">Text to hide</label><input id="hdText" value="CODE BREAKER" maxlength="40"></div>
    <div><label for="hdCar">Carrier</label><select id="hdCar"><option value="noise">Noise</option><option value="song">Synthetic birdsong</option><option value="sweep">Tone sweep</option><option value="none">Nothing (picture only)</option></select></div>
    <div><label for="hdLvl">Level, dB below the carrier</label><input id="hdLvl" type="number" value="-10" min="-40" max="10"></div></div>
    <button id="hdGo">Hide it</button><div id="hdOut" aria-live="polite"></div>
    <h3>Look for a hidden picture</h3><label class="filebtn">Choose a recording<input id="hdFile" type="file" accept="audio/*"></label><div id="hdRev" aria-live="polite"></div></div>`;
}

function hiddenWire() {
  $("#hdGo").onclick = ev => busy(ev.target, $("#hdOut"), async () => {
    const r = await api("/sounds/hide", { text: $("#hdText").value, carrier: $("#hdCar").value, level: +$("#hdLvl").value });
    $("#hdOut").innerHTML = `<audio controls src="${r.wav}"></audio> <a href="${r.wav}" download="hidden.wav">Save the sound</a><img src="${r.spectrogram}" alt="Spectrogram of the sound" style="width:100%;margin-top:8px">`;
  });
  $("#hdFile").onchange = e => { const f = e.target.files[0]; if (!f) return; const rd = new FileReader(); rd.onload = () => busy($("#hdGo"), $("#hdRev"), async () => {
    const r = await api("/sounds/reveal", { data: rd.result });
    $("#hdRev").innerHTML = `<img src="${r.image}" alt="Spectrogram of the recording" style="width:100%">
      <p>${r.words.length ? `Words read in the spectrogram: <b>${r.words.map(w => esc(w.text)).join(", ")}</b>.` : "No words read in the spectrogram."} Structure score ${esc(r.structure)} (clean noise stays under 0.5, synthetic birdsong under 38, a tone sweep under 7.3; a hidden picture raises it, but the score depends on the kind of sound, so judge it against similar recordings).</p>`;
  }); rd.readAsDataURL(f); };
}

route(/^\/sounds$/, async () => {
  view().innerHTML = `<p class="kicker">// SOUND LAB</p><h1>Sound Lab</h1><p class="lead">Birdsong is a signal with an alphabet of syllables and rules for ordering them. This page turns a recording into that sequence, measures it, and asks two neural networks what made the sound.</p>
    <div class="panel"><div class="row"><div><label for="sndX">Example recording</label><select id="sndX"></select></div></div><button id="sndGo">Analyse example</button>
    <label class="filebtn">Open an audio file<input id="sndF" type="file" accept="audio/*,.wav,.mp3,.ogg,.flac"></label> <button id="sndRec" class="alt">Record 10 seconds</button><button id="sndStop" class="alt" disabled>Stop recording</button><p id="sndMsg" class="mute" aria-live="polite"></p></div><div id="sndOut"></div>
    <p class="mute">More on birdsong as a code: <a href="#/biology">Codes in Nature</a>. Models: BirdNET 2.4 (Cornell Lab of Ornithology and Chemnitz University of Technology; non-commercial licence) and YAMNet (Google). Audio stays on this computer.</p>`;
  const ex = await api("/sounds/examples");
  $("#sndX").innerHTML = ex.map(e => `<option value="${esc(e.id)}">${esc(e.title)}</option>`).join("");
  $("#sndGo").onclick = ev => busy(ev.target, $("#sndMsg"), () => sndRun({ example: $("#sndX").value }));
  $("#sndF").onchange = ev => busy(ev.target.parentElement, $("#sndMsg"), async () => {
    const f = ev.target.files[0]; if (!f) return;
    if (f.size > 40 * 1024 * 1024) throw new Error("That file is too large here (40 MB limit).");
    await sndRun({ data: sndB64(await f.arrayBuffer()) });
  });
  const stopRec = () => { if (SND.rec && SND.rec.state === "recording") SND.rec.stop(); };
  $("#sndStop").onclick = stopRec;
  $("#sndRec").onclick = async () => {
    try {
      SND.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false } });
      SND.chunks = []; SND.rec = new MediaRecorder(SND.stream);
      SND.rec.ondataavailable = e => SND.chunks.push(e.data);
      SND.rec.onstop = async () => {
        SND.stream.getTracks().forEach(t => t.stop()); $("#sndRec").disabled = false; $("#sndStop").disabled = true;
        try {
          const ac = new AudioContext(), audio = await ac.decodeAudioData(await new Blob(SND.chunks).arrayBuffer());
          await sndRun({ data: sndB64(sndWav(audio.getChannelData(0), audio.sampleRate)) }); ac.close();
        } catch (e) { $("#sndMsg").innerHTML = `<span class="err">${esc(e.message)}</span>`; }
      };
      SND.rec.start(); $("#sndRec").disabled = true; $("#sndStop").disabled = false; $("#sndMsg").textContent = "Recording…";
      setTimeout(stopRec, 10000);
    } catch (e) { $("#sndMsg").innerHTML = `<span class="err">${esc(e.message)}. Allow microphone access for this page.</span>`; }
  };
  const leave = () => { if (!location.hash.startsWith("#/sounds")) { stopRec(); removeEventListener("hashchange", leave); } };
  addEventListener("hashchange", leave);
  view().insertAdjacentHTML("beforeend", hiddenPanel());
  hiddenWire();
}, "sounds");
