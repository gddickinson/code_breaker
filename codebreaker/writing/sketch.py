"""Drawing pad support (Round 79): a sign sketched with a mouse or finger, identified by the glyph recogniser.

A sketch differs from a font drawing: even, thin strokes, wobbly lines, no filled areas. The control simulates one:
the sign's morphological skeleton (Lantuéjoul: what each erosion removes beyond an opening) redrawn with a pen of
random width and a smooth wobble, and measures top-1 and top-5 per script."""
import json

import cv2
import numpy as np

from ..languages import ROOT
from .glyph_model import probabilities
from .glyph_render import _elastic, classes, fit, prep, raw
from .script_id import identify

RESULT = ROOT / "data/results/sketch_eval.json"


def skeleton(a: np.ndarray) -> np.ndarray:
    img = (a > 100).astype(np.uint8) * 255
    k, skel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3)), np.zeros_like(img)
    while img.any():
        er = cv2.erode(img, k)
        skel |= cv2.subtract(img, cv2.dilate(er, k))
        img = er
    return skel


def simulate(a: np.ndarray, rnd: np.random.Generator) -> np.ndarray:
    big = fit(a, 192, margin=20)
    sk = skeleton(big)
    pen = int(rnd.integers(5, 11))
    drawn = cv2.dilate(sk, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (pen, pen)))
    drawn = _elastic(drawn, rnd, 4.0, 8.0)
    return prep(fit(drawn))


def crop_sign(gray: np.ndarray) -> np.ndarray | None:
    """Pad picture (any polarity) -> ink-bright crop of everything drawn; None if empty."""
    g = gray if gray.mean() < 128 else 255 - gray
    ys, xs = np.nonzero(g > 60)
    if len(xs) < 5:
        return None
    return g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def identify_sketch(gray: np.ndarray, scripts: list[str] | None = None, top: int = 10) -> dict:
    c = crop_sign(gray)
    if c is None:
        return {"candidates": [], "script": None, "note": "Nothing drawn yet."}
    p = probabilities(prep(fit(c))[None])[0]
    cls = classes()
    if scripts:
        p = p * np.array([x["script"] in scripts for x in cls])
        p = p / max(p.sum(), 1e-9)
    order = np.argsort(-p)[:top]
    return {"candidates": [{"sign": cls[k]["signs"][0], "script": cls[k]["script"], "values": cls[k]["values"], "code": cls[k]["code"],
                            "name": cls[k]["name"], "p": round(float(p[k]), 3)} for k in order],
            "script": identify(p[None])["ranking"][:3], "note": "Suggestions for a sketched sign; the recogniser learned from font drawings."}


def evaluate(per_script: int = 25, seed: int = 79) -> dict:
    rnd, cls = np.random.default_rng(seed), classes()
    out = {}
    for s in sorted({c["script"] for c in cls}):
        pool = [k for k, c in enumerate(cls) if c["script"] == s]
        ks = [int(rnd.choice(pool)) for _ in range(per_script)]
        imgs = np.stack([simulate(raw(cls[k]["signs"][0], s), rnd) for k in ks])
        p = probabilities(imgs)
        allowed = np.array([c["script"] == s for c in cls])
        top_all, top_in = np.argsort(-p, 1)[:, :5], np.argsort(-(p * allowed), 1)[:, :5]
        out[s] = {"top1": round(float(np.mean(top_all[:, 0] == ks)), 2), "top5": round(float(np.mean([k in t for k, t in zip(ks, top_all)])), 2),
                  "top5_within_script": round(float(np.mean([k in t for k, t in zip(ks, top_in)])), 2)}
    return {"id": "sketch_eval", "per_script": per_script, "by_script": out,
            "mean_top5_within_script": round(float(np.mean([v["top5_within_script"] for v in out.values()])), 3)}


if __name__ == "__main__":
    r = evaluate()
    RESULT.write_text(json.dumps(r, indent=1))
    print(json.dumps(r, indent=1))
