/* Audio Signals: DTMF, Morse and APRS decoded from sound, with the code identified automatically. */
function acShow(r) {
  const best = r.ranking[0], rel = r.reliability, pk = best.detail && best.detail.packets;
  $("#acOut").innerHTML = `<div class="panel cverdict ${best.score ? "readable" : "none"}"><h3>${best.score ? esc(best.code) : "No code recognised"}</h3>${best.score ? `<p class="reading">${esc(best.text)}</p>` : '<p>Nothing decoded. The sound may be too noisy, or use a code not tried here.</p>'}
      ${r.truth && r.truth.text ? `<p class="mute">Sent: ${esc(r.truth.text)}</p>` : ""}${r.audio ? `<audio controls src="${r.audio}" style="width:100%;margin-top:8px"></audio>` : ""}</div>
    ${pk && pk.length ? `<div class="panel"><h3>Packets</h3>${table(["From", "To", "Path", "Message"], pk.map(p => [p.source, p.destination, p.path.join(", "), p.info]))}<p class="mute">Each packet passed its CRC-16 frame check.</p></div>` : ""}
    <div class="panel"><h3>Every code tried</h3>${table(["Code", "Score", "Decoded"], r.ranking.map(x => [x.code, x.score, x.text.slice(0, 60)]))}<p class="mute">Control: ${rel.correct} of ${rel.trials} generated recordings decoded exactly; ${rel.null_decoded} of ${rel.null_trials} noise and stray-tone recordings were wrongly decoded.</p></div>`;
}

route(/^\/audio$/, async () => {
  view().innerHTML = `<p class="kicker">// AUDIO SIGNALS</p><h1>Audio signals</h1><p class="lead">Telephones, radio operators and amateur radio trackers all send data as sound. This page recognises which code a recording uses and decodes it.</p>
    <div class="panel"><div class="row"><div><label for="acK">Generate</label><select id="acK"><option value="dtmf">DTMF touch tones</option><option value="morse" selected>Morse code</option><option value="aprs">APRS packet (1200 baud AFSK)</option></select></div>
    <div><label for="acM">Message</label><input id="acM" value="CQ DE CODE BREAKER"></div><div><label for="acN">Noise: <b id="acNv"></b></label><input id="acN" type="range" min="0" max="0.6" step="0.05" value="0.1"></div></div>
    <button id="acGo">Generate and decode</button> <label class="filebtn">Or open a recording<input id="acF" type="file" accept="audio/*,.wav,.mp3,.ogg,.flac"></label> <button id="acRec" class="alt">Record 8 seconds</button><p id="acMsg" aria-live="polite"></p></div><div id="acOut"></div>
    <div class="biogrid"><div class="panel"><h3>DTMF</h3><p>Each key is a pair of tones, one from a low group of four and one from a high group of four, so 16 keys need only 8 frequencies. Decoding measures those 8 with the Goertzel algorithm.</p></div><div class="panel"><h3>Morse</h3><p>A dash lasts three dots, a gap inside a letter one dot, between letters three, between words seven. The decoder finds the dot length from the recording itself, so it adapts to any speed.</p></div><div class="panel"><h3>APRS</h3><p>Amateur radio position reports: AX.25 frames with CRC-16, sent as 1200 and 2200 Hz tones at 1200 bits per second. A change of tone means 0 and no change means 1.</p></div></div>`;
  const lab = () => { $("#acNv").textContent = (+$("#acN").value).toFixed(2); };
  $("#acN").oninput = lab; lab();
  $("#acK").onchange = () => { $("#acM").value = { dtmf: "0123456789*#", morse: "CQ DE CODE BREAKER", aprs: "Hello from Code Breaker" }[$("#acK").value]; };
  $("#acGo").onclick = ev => busy(ev.target, $("#acMsg"), async () => acShow(await api("/signals/audio", { example: $("#acK").value, message: $("#acM").value, noise: +$("#acN").value })));
  $("#acF").onchange = ev => busy(ev.target.parentElement, $("#acMsg"), async () => { const f = ev.target.files[0]; if (f) acShow(await api("/signals/audio", { data: sndB64(await f.arrayBuffer()) })); });
  $("#acRec").onclick = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false } }), rec = new MediaRecorder(stream), chunks = [];
      rec.ondataavailable = e => chunks.push(e.data);
      rec.onstop = async () => { stream.getTracks().forEach(t => t.stop()); const ac = new AudioContext(), a = await ac.decodeAudioData(await new Blob(chunks).arrayBuffer()); acShow(await api("/signals/audio", { data: sndB64(sndWav(a.getChannelData(0), a.sampleRate)) })); ac.close(); $("#acRec").disabled = false; };
      rec.start(); $("#acRec").disabled = true; $("#acMsg").textContent = "Recording…"; setTimeout(() => rec.stop(), 8000);
    } catch (e) { $("#acMsg").innerHTML = `<span class="err">${esc(e.message)}. Allow microphone access for this page.</span>`; }
  };
}, "audio");
