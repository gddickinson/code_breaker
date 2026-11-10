"""Video Signals page: generated captures, decoding with previews, the control, and one line drawn with its parts."""
import base64
import json

import cv2
import numpy as np

from ..languages import ROOT
from . import video as V
from .raw_detect import scene

RESULT = ROOT / "data/results/video_control.json"


def _png(img: np.ndarray) -> str:
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR) if img.ndim == 3 else img
    ok, buf = cv2.imencode(".png", bgr)
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode()


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    a = cv2.resize(a, (b.shape[1], b.shape[0]), interpolation=cv2.INTER_AREA)
    return float(np.corrcoef(a.reshape(-1).astype(float), b.reshape(-1).astype(float))[0, 1])


def _line_trace(ch: dict, fs: float, mode: str) -> dict:
    """Two lines of the red channel and the line sync, with the standard's porches for labelling."""
    hst, _, _ = V._pulses(ch["HSYNC"])
    if len(hst) < 40:
        return {}
    a, b = hst[30], hst[32]
    step = max(1, (b - a) // 600)
    hv, hf, hs, hb, *_rest = V.MODES[mode]
    pclk = V.MODES[mode][8]
    return {"red": [round(float(v), 3) for v in ch["R"][a:b:step]], "sync": [int(v > 0.5) for v in ch["HSYNC"][a:b:step]], "parts_us": {"sync": hs / pclk * 1e6, "back porch": hb / pclk * 1e6, "picture": hv / pclk * 1e6, "front porch": hf / pclk * 1e6}}


def example(kind: str, factor: float = 1.0, noise: float = 0.02, seed: int = 3) -> dict:
    rnd = np.random.default_rng(seed)
    if kind == "composite":
        truth = cv2.cvtColor(scene(480, 240, seed), cv2.COLOR_RGB2GRAY)
        fs = 13.5e6 * factor
        r = V.composite_decode(V.composite_signal(truth, fs, noise, rnd), fs)
        return {"kind": "composite", "ok": r["ok"], "measured": r.get("measured", {}), "reason": r.get("reason", ""), "image": _png(r["image"]) if r.get("image") is not None else None, "sent": _png(truth), "match": round(_corr(r["image"], truth), 3) if r.get("image") is not None else None, "fs_mhz": fs / 1e6}
    hv, vv = V.MODES[kind][0], V.MODES[kind][4]
    truth = scene(hv, vv, seed)
    ch, fs = V.vga_signal(truth, kind, factor, noise, rnd)
    r = V.vga_decode(ch, fs)
    return {"kind": kind, "ok": r["ok"], "mode": r["mode"], "closest": r["closest"], "confidence": r["confidence"], "measured": r["measured"], "reason": r["reason"], "image": _png(r["image"]) if r.get("image") is not None else None, "sent": _png(cv2.resize(truth, (min(hv, 640), int(vv * min(hv, 640) / hv)))), "match": round(_corr(r["image"], truth), 3) if r.get("image") is not None else None, "fs_mhz": round(fs / 1e6, 3), "trace": _line_trace(ch, fs, kind)}


def control() -> dict:
    rows = []
    for mode in V.MODES:
        for factor in (0.8, 1.0, 1.4):
            for noise in (0.01, 0.05):
                r = example(mode, factor, noise, len(rows) + 11)
                rows.append({"kind": mode, "ok": r["ok"] and r["mode"] == mode, "match": r["match"]})
    for factor in (0.6, 1.0, 1.5):
        for noise in (0.01, 0.04):
            r = example("composite", factor, noise, len(rows) + 11)
            rows.append({"kind": "composite", "ok": r["ok"], "match": r["match"]})
    rnd, false = np.random.default_rng(5), 0
    for t in range(10):
        n = 300000
        ch = {c: rnd.normal(0.3, 0.2, n).astype(np.float32) for c in "RGB"}
        ch["HSYNC"] = (rnd.random(n) > rnd.uniform(0.3, 0.97)).astype(np.float32)
        ch["VSYNC"] = (rnd.random(n) > rnd.uniform(0.3, 0.99)).astype(np.float32)
        false += V.vga_decode(ch, 25e6).get("ok", False) or V.composite_decode(rnd.normal(0.5, 0.2, n).astype(np.float32), 13.5e6).get("ok", False)
    ok = [r for r in rows if r["ok"]]
    return {"cases": len(rows), "decoded": len(ok), "mean_match": round(float(np.mean([r["match"] for r in ok])), 3) if ok else 0.0, "worst_match": round(float(min(r["match"] for r in ok)), 3) if ok else 0.0, "null_trials": 10, "null_decoded": int(false), "rows": rows}


def reliability() -> dict:
    if not RESULT.exists():
        RESULT.write_text(json.dumps(control(), indent=1))
    d = json.loads(RESULT.read_text())
    return {k: d[k] for k in ("cases", "decoded", "mean_match", "worst_match", "null_trials", "null_decoded")}
