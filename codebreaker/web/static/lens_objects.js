/* Lens object understanding (Round 90b): what the main object is, its box, and tracking it in the live view.
   The local vision model answers when one is installed; otherwise MobileNetV2 and GrabCut do. The mode is shown. */
let lensTrack = null;  // {label} while an object is tracked in the live view

function lensFrameUrl() {  /* the picture on screen: the live frame (as the live loop sends it) or the shown image */
  const v = $("#lnVid"), img = $("#lnImg");
  const c = document.createElement("canvas");
  if (lensStream && v.videoWidth) {
    const s = Math.min(1, 960 / v.videoWidth);
    c.width = v.videoWidth * s; c.height = v.videoHeight * s;
    c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
  } else if (!img.hidden && img.naturalWidth) {
    c.width = img.naturalWidth; c.height = img.naturalHeight;
    c.getContext("2d").drawImage(img, 0, 0);
  } else return null;
  return c.toDataURL("image/jpeg", 0.9);
}

async function lensObject(ev) {
  const url = lensFrameUrl();
  if (!url) { $("#lnObjOut").innerHTML = '<p class="mute">Start the camera or open a picture first.</p>'; return; }
  await busy(ev.target, $("#lnObjOut"), async () => {
    lensLogAdd(["object: asking what the main object is"]);
    const live = !!lensStream;
    const r = await api("/lens/object", { image: url, ai: true, session: lensSession || "objects", track: live });
    const label = r.label || "no recognisable object";
    $("#lnObjOut").innerHTML = `<h3>Object</h3><p><b>${esc(label)}</b>${r.description ? ` · ${esc(r.description)}` : ""}</p>
      <p class="mute">Mode: ${esc(r.mode)}${r.seconds ? ` (${esc(r.seconds)} s)` : ""}. ${r.box ? "Its box is drawn on the picture." : "No outline found."}
      ${r.tracking ? " Tracking it in the live view: move the camera." : ""}</p>
      ${r.candidates ? table(["ImageNet class", "Probability"], r.candidates.map(c => [c.label, c.p])) : ""}`;
    if (r.box) lensOverlaySet([{ kind: "object", label, box: r.box }], r.size[0], label, live);
    lensTrack = r.tracking ? { label, session: lensSession || "objects" } : null;
    lensLogAdd([`object: ${label} (${r.mode})`]);
  });
}

async function lensTrackStep(dataUrl) {  /* called from the live loop; returns an overlay item or null */
  if (!lensTrack) return null;
  try {
    const t = await api("/lens/track", { image: dataUrl, session: lensTrack.session });
    if (t.lost) { lensLogAdd([`object lost (match ${t.score})`]); return null; }
    return { kind: "object", label: lensTrack.label, box: t.box };
  } catch (e) { lensTrack = null; return null; }
}
