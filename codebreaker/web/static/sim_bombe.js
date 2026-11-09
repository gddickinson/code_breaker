/* The bombe demonstration: spinning drums, then the settings the search stopped on. */
route(/^\/machine\/bombe$/, async () => {
  view().innerHTML = `${backLink}<h1>The Bletchley bombe</h1>
    <p class="lead">Guess a short stretch of plaintext, called a crib. For each rotor setting, assume one plugboard connection, follow what it implies, and throw the setting out at the first contradiction. Turing and Welchman's insight is that a wrong guess destroys itself.</p>
    <div class="panel"><p>Each run encrypts a passage on a random machine with eight plug pairs, then gives the bombe the first 32 letters as a crib.</p><button id="go">Run the bombe</button></div>
    <div class="windows" id="drums" aria-hidden="true">${["Left", "Middle", "Right"].map(n => `<div class="window"><small>${n}</small><b>A</b></div>`).join("")}</div><div id="o"></div>`;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  $("#go").onclick = ev => busy(ev.target, $("#o"), async () => {
    const drums = [...document.querySelectorAll("#drums b")];
    const spin = reduce ? null : setInterval(() => drums.forEach(d => { d.textContent = AZ[Math.floor(Math.random() * 26)]; }), 45);
    $("#o").innerHTML = '<p class="mute">Testing every rotor order and start position…</p>';
    let r;
    try { r = await api("/machines/bombe"); } finally { if (spin) clearInterval(spin); }
    [...r.found_start].forEach((c, i) => { drums[i].textContent = c; });
    const same = JSON.stringify(r.plugboard) === JSON.stringify(r.found_plugboard);
    $("#o").innerHTML = `<p><span class="tag ${r.success ? "good" : "bad"}">${r.success ? "Message recovered" : "Not recovered"}</span></p>
      <div class="tiles"><div class="tile"><b>${r.found_positions_tested.toLocaleString()}</b><span>Rotor positions tested</span></div><div class="tile"><b>${r.found_stops}</b><span>Stops</span></div><div class="tile"><b>${Math.round(r.accuracy * 100)}%</b><span>Letters recovered</span></div></div>
      <div class="panel"><h3>Crib given to the bombe</h3><pre>${esc(r.crib)}</pre><h3>Ciphertext</h3><pre>${esc(r.ciphertext.slice(0, 200))}…</pre>
      ${table(["", "Rotors", "Start", "Plugboard"], [["Hidden machine", r.rotors, r.start, r.plugboard.join(" ")], ["Bombe found", r.found_rotors, r.found_start, r.found_plugboard.join(" ")]])}
      <p>${same ? "Every plug pair matches." : "The plugboard differs: unused letters can pair differently without changing the crib."}</p>
      <h3>Message</h3><pre>${esc(r.found_plaintext)}</pre></div>
      <p class="mute">This model assumes ring settings of A. Real wartime keys also needed ring recovery.</p>`;
  });
}, "machines");
