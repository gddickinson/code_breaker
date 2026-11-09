/* Theory simulations for error correction: detection, Hamming, Reed-Solomon and Viterbi against Shannon's limit. */
THSIMS.parity = el => {
  el.innerHTML = `<label for="eT">Message</label><input id="eT" value="Meet at dawn"><p class="mute">Select bits below to flip them, as noise would.</p><div id="eB" class="bitrow" style="flex-wrap:wrap"></div><div id="eO"></div>
    <h3>Check digits</h3><div class="row"><div><label for="eL">Card-style number (Luhn)</label><input id="eL" value="4539 1488 0343 6467"></div><div><label for="eI">ISBN-10</label><input id="eI" value="0-306-40615-2"></div></div><p id="eD" class="reading"></p>`;
  let sent = [], rx = [];
  const draw = () => {
    $("#eB").innerHTML = rx.map((v, i) => `<button type="button" data-i="${i}" class="${v !== sent[i] ? "bad" : ""}" style="min-width:22px">${v}</button>`).join("");
    document.querySelectorAll("#eB button").forEach(b => { b.onclick = () => { rx[+b.dataset.i] ^= 1; draw(); }; });
    const flips = rx.reduce((a, v, i) => a + (v !== sent[i]), 0), par = ECC_PARITY(sent) !== ECC_PARITY(rx), crc = crcBits(sent, CRC8).join("") !== crcBits(rx, CRC8).join("");
    $("#eO").innerHTML = table(["Bits flipped", "Single parity bit", "CRC-8"], [[flips, par ? "error detected" : flips ? "missed" : "no error", crc ? "error detected" : flips ? "missed" : "no error"]]);
  };
  const reset = () => { sent = textBits($("#eT").value.slice(0, 12)); rx = [...sent]; draw(); };
  const digits = () => { $("#eD").textContent = `Luhn: ${luhnValid($("#eL").value) ? "valid" : "invalid"}. ISBN-10: ${isbn10Valid($("#eI").value) ? "valid" : "invalid"}. Change any single digit and each check fails.`; };
  $("#eT").oninput = reset; $("#eL").oninput = digits; $("#eI").oninput = digits; reset(); digits();
};

THSIMS.hamming = el => {
  let data = [1, 0, 1, 1], flip = -1;
  el.innerHTML = `<p class="mute">Choose 4 data bits, then flip any one of the 7 sent bits. Positions 1, 2 and 4 hold parity.</p><div class="row"><div><h4>Data</h4><div id="hD" class="bitrow"></div></div><div><h4>Received codeword</h4><div id="hC" class="bitrow"></div></div></div><div id="hO"></div>`;
  const draw = () => {
    const c = hamming74Encode(data), rx = [...c];
    if (flip >= 0) rx[flip] ^= 1;
    const d = hamming74Decode(rx);
    $("#hD").innerHTML = data.map((v, i) => `<button type="button" data-i="${i}">${v}</button>`).join("");
    $("#hC").innerHTML = rx.map((v, i) => `<button type="button" data-i="${i}" class="${i === flip ? "bad" : ""}" title="Position ${i + 1}${[0, 1, 3].includes(i) ? ", parity" : ", data"}">${v}</button>`).join("");
    document.querySelectorAll("#hD button").forEach(b => { b.onclick = () => { data[+b.dataset.i] ^= 1; draw(); }; });
    document.querySelectorAll("#hC button").forEach(b => { b.onclick = () => { flip = flip === +b.dataset.i ? -1 : +b.dataset.i; draw(); }; });
    $("#hO").innerHTML = `<p class="reading">Syndrome ${d.syndrome.toString(2).padStart(3, "0")} = ${d.syndrome} ${d.syndrome ? `→ flip position ${d.syndrome}` : "→ no error"}. Recovered data: ${d.data.join("")} ${d.data.join("") === data.join("") ? "(correct)" : "(wrong)"}.</p>`;
  };
  draw();
};

THSIMS.reedsolomon = el => {
  el.innerHTML = `<div class="row"><div><label for="rM">Message</label><input id="rM" value="REED-SOLOMON"></div><div><label for="rN">Check bytes: <b id="rNv"></b></label><input id="rN" type="range" min="2" max="16" step="2" value="8"></div><div><label for="rE">Bytes corrupted: <b id="rEv"></b></label><input id="rE" type="range" min="0" max="12" value="3"></div></div><button id="rGo" class="alt">Corrupt different bytes</button><div id="rO"></div>`;
  let seed = 1;
  const draw = () => {
    const nsym = +$("#rN").value, k = +$("#rE").value, msg = [...new TextEncoder().encode($("#rM").value.slice(0, 40))];
    $("#rNv").textContent = nsym; $("#rEv").textContent = k;
    const enc = rsEncode(msg, nsym), rx = [...enc], r = eccRng(seed), hit = new Set();
    while (hit.size < Math.min(k, rx.length)) hit.add(Math.floor(r() * rx.length));
    hit.forEach(p => { rx[p] ^= 1 + Math.floor(r() * 255); });
    const d = rsDecode(rx, nsym), show = a => a.map(v => (v >= 32 && v < 127 ? String.fromCharCode(v) : "·")).join("");
    const cells = rx.map((v, i) => `<span style="display:inline-block;width:20px;text-align:center;font-family:var(--mono);${hit.has(i) ? "background:var(--c2);color:#fff;" : i >= msg.length ? "color:var(--mute);" : ""}">${v >= 32 && v < 127 ? esc(String.fromCharCode(v)) : "·"}</span>`).join("");
    $("#rO").innerHTML = `<h4>Received (corrupted bytes highlighted, check bytes in grey)</h4><p>${cells}</p><p class="reading">${d.ok ? `Decoded: ${esc(show(d.data))} ${show(d.data) === show(msg) ? "(correct)" : "(wrong)"}` : `Cannot decode: ${esc(d.reason)}`}</p>
      <p class="mute">With ${nsym} check bytes up to ${nsym / 2} corrupted bytes can be corrected anywhere in the block. Beyond that the decoder usually reports failure rather than guessing.</p>`;
  };
  ["rM", "rN", "rE"].forEach(i => { $(`#${i}`).oninput = draw; });
  $("#rGo").onclick = () => { seed++; draw(); };
  draw();
};

THSIMS.viterbi = el => {
  el.innerHTML = `<label for="vP">Channel error rate: <b id="vPv"></b></label><input id="vP" type="range" min="0" max="0.2" step="0.005" value="0.05"><div id="vO"></div>`;
  const draw = () => {
    const p = +$("#vP").value, r = berCompare(p, 6000, 7);
    $("#vPv").textContent = `${(p * 100).toFixed(1)}%`;
    const max = Math.max(...r.schemes.map(s => s.ber), 1e-4);
    $("#vO").innerHTML = `${r.schemes.map(s => `<div style="display:grid;grid-template-columns:200px 1fr 130px;gap:10px;align-items:center;margin:6px 0"><span>${esc(s.name)} <span class="mute">rate ${s.rate.toFixed(2)}</span></span><div style="background:rgba(255,255,255,.05);height:14px"><div style="width:${s.ber / max * 100}%;height:14px;background:var(--c1);border-radius:0 3px 3px 0" title="${(s.ber * 100).toFixed(2)}% errors"></div></div><b>${(s.ber * 100).toFixed(2)}% errors</b></div>`).join("")}
      <p class="reading">Shannon capacity of this channel: ${r.capacity.toFixed(3)} bits per bit sent.</p><p class="mute">Shannon proved that codes exist with rates up to the capacity and error rates as small as you like. Simple codes trade a lot of rate for modest gains; modern LDPC and turbo codes, decoded by belief propagation, come within a fraction of a decibel of the limit.</p>`;
  };
  $("#vP").oninput = draw; draw();
};
