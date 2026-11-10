/* Aircraft: decode ADS-B broadcasts into a picture of the sky. */
function abMap(planes, truth) {
  const pts = planes.filter(p => p.lat !== undefined), W = 640, H = 380;
  const all = [...pts, ...(truth || [])];
  if (!all.length) return '<p class="mute">No positions decoded.</p>';
  const lats = all.map(p => p.lat), lons = all.map(p => p.lon), la0 = Math.min(...lats) - 0.2, la1 = Math.max(...lats) + 0.2, lo0 = Math.min(...lons) - 0.3, lo1 = Math.max(...lons) + 0.3;
  const x = lo => 30 + (lo - lo0) / (lo1 - lo0) * (W - 60), y = la => H - 30 - (la - la0) / (la1 - la0) * (H - 60);
  const arrow = p => p.heading === undefined ? "" : `<line x1="${x(p.lon)}" y1="${y(p.lat)}" x2="${x(p.lon) + 18 * Math.sin(p.heading * Math.PI / 180)}" y2="${y(p.lat) - 18 * Math.cos(p.heading * Math.PI / 180)}" stroke="var(--c1)" stroke-width="2"/>`;
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;background:#05040e" role="img" aria-label="Decoded aircraft positions">${(truth || []).map(t => `<circle cx="${x(t.lon)}" cy="${y(t.lat)}" r="9" fill="none" stroke="var(--mute)" stroke-dasharray="3 3"><title>Sent: ${esc(t.callsign)}</title></circle>`).join("")}
    ${pts.map(p => `${arrow(p)}<circle cx="${x(p.lon)}" cy="${y(p.lat)}" r="5" fill="var(--c2)" stroke="var(--panel)" stroke-width="2"><title>${esc(p.callsign || p.icao)}: ${p.alt} ft</title></circle><text x="${x(p.lon) + 8}" y="${y(p.lat) - 8}" fill="var(--ink)" font-size="12">${esc(p.callsign || p.icao)}</text>`).join("")}
    <text x="30" y="${H - 8}" fill="var(--mute)" font-size="11">${lo0.toFixed(1)}°</text><text x="${W - 30}" y="${H - 8}" text-anchor="end" fill="var(--mute)" font-size="11">${lo1.toFixed(1)}°</text></svg><p class="mute">Filled dots are decoded positions with heading lines; dashed circles mark where the aircraft really were.</p>`;
}

function abShow(r) {
  const rel = r.reliability, planes = r.planes || [];
  const head = r.messages !== undefined ? `<p>${r.decoded} of ${r.messages} messages passed the CRC (${(r.planes || []).length} aircraft heard); ${r.aircraft_right} of ${r.truth.length} aircraft were decoded completely and correctly.</p>` : "";
  $("#abOut").innerHTML = `<div class="panel">${head}${abMap(planes, r.truth)}</div>
    <div class="panel"><h3>Aircraft heard</h3>${table(["Address", "Callsign", "Altitude (ft)", "Latitude", "Longitude", "Speed (kt)", "Heading", "Climb (ft/min)", "Messages"], planes.map(p => [p.icao, p.callsign || "", p.alt ?? "", p.lat ?? "", p.lon ?? "", p.speed ?? "", p.heading ?? "", p.vrate ?? "", p.messages]))}
    ${r.frames ? table(["Message", "Type", "CRC"], r.frames.map(f => [f.hex, f.kind || `DF ${f.df}`, f.crc_ok ? "correct" : "wrong"])) : ""}
    <p class="mute">Control: ${rel.aircraft_right} of ${rel.aircraft} aircraft decoded completely across noise levels from low to high; most failures are at high noise, where messages are lost rather than misread. ${rel.null_frames} false messages from noise.</p></div>`;
}

route(/^\/adsb$/, async () => {
  view().innerHTML = `<p class="kicker">// AIRCRAFT</p><h1>Aircraft (ADS-B)</h1><p class="lead">Airliners broadcast their identity, position, altitude and velocity about twice a second on 1090 MHz. Each message carries a 24-bit CRC, which both rejects damaged messages and can repair a single wrong bit.</p>
    <div class="panel"><div class="row"><div><label for="abN">Aircraft</label><input id="abN" type="number" min="1" max="20" value="6"></div><div><label for="abZ">Noise: <b id="abZv"></b></label><input id="abZ" type="range" min="0" max="0.4" step="0.01" value="0.1"></div><div><label for="abS">Scene</label><input id="abS" type="number" min="1" value="1"></div></div>
    <button id="abGo">Generate the sky and decode it</button><label for="abH">Or paste messages in hex</label><textarea id="abH" rows="3">8D4840D6202CC371C32CE0576098 8D40621D58C382D690C8AC2863A7 8D40621D58C386435CC412692AD6 8D485020994409940838175B284F</textarea><button id="abP" class="alt">Decode pasted messages</button><p id="abMsg" aria-live="polite"></p></div><div id="abOut"></div>
    <p class="mute">The pasted examples are the worked examples from Junzi Sun's The 1090 MHz Riddle: KLM1023, a position over the North Sea at 38,000 ft, and a velocity. Two of them come from different aircraft, so the position pair has no callsign.</p>`;
  const lab = () => { $("#abZv").textContent = (+$("#abZ").value).toFixed(2); };
  $("#abZ").oninput = lab; lab();
  $("#abGo").onclick = ev => busy(ev.target, $("#abMsg"), async () => abShow(await api("/signals/adsb", { aircraft: +$("#abN").value, noise: +$("#abZ").value, seed: +$("#abS").value })));
  $("#abP").onclick = ev => busy(ev.target, $("#abMsg"), async () => abShow(await api("/signals/adsb", { hex: $("#abH").value })));
}, "adsb");
