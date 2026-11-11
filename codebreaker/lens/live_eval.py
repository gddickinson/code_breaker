"""Control for live sessions (Round 78b): a synthetic video of a label that moves, rotates and changes light.

A card with six known text lines on a textured background is filmed over 24 frames: rotation sweeping -20 to +20
degrees, drifting position, brightness from 0.55 to 1.3, a moving glare band, occasional blur, JPEG compression.
Reported: share of lines read exactly in single frames (RapidOCR alone) against the session's consensus at the end;
mean distance between tracked line centres and the true ones (as a share of line height); thorough readings used."""
import json
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..languages import ROOT
from . import live_session as L

RESULT = ROOT / "data/results/lens_live_eval.json"
LINES = ["NATURAL FLAVORS", "Serving size 1 mint", "Total Sugars 1g", "MADE OF SUGAR AND GUM", "Questions call today", "Keep in a cool dry place"]
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"


def card(seed: int = 78) -> tuple[np.ndarray, list[np.ndarray]]:
    rnd = np.random.default_rng(seed)
    w, h = 700, 460
    base = np.clip(rnd.normal(200, 18, (h, w)), 0, 255).astype(np.uint8)
    base = cv2.GaussianBlur(base, (0, 0), 1.2)  # paper texture: features for alignment
    im = Image.fromarray(base)
    d = ImageDraw.Draw(im)
    d.rectangle([8, 8, w - 8, h - 8], outline=40, width=4)
    for _ in range(40):
        x, y = rnd.integers(20, w - 20, 2)
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=int(rnd.integers(60, 140)))
    quads = []
    for i, t in enumerate(LINES):
        f = ImageFont.truetype(FONT, 34 if i == 0 else 26)
        x, y = 40, 30 + i * 70
        d.text((x, y), t, font=f, fill=25)
        x0, y0, x1, y1 = d.textbbox((x, y), t, font=f)
        quads.append(np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]))
    return np.asarray(im), quads


def frames(n: int = 24, seed: int = 78):
    rnd = np.random.default_rng(seed)
    c, quads = card(seed)
    W, H = 960, 720
    for k in range(n):
        ang = -20 + 40 * k / (n - 1)
        tx, ty = 130 + 60 * np.sin(k / 4), 120 + 40 * np.cos(k / 5)
        M = cv2.getRotationMatrix2D((c.shape[1] / 2, c.shape[0] / 2), ang, 1.0)
        M[:, 2] += (tx, ty)
        bg = np.full((H, W), 120, np.uint8)
        img = cv2.warpAffine(c, M, (W, H), dst=bg.copy(), borderMode=cv2.BORDER_TRANSPARENT).astype(np.float32)
        gain = 0.55 + 0.75 * (0.5 + 0.5 * np.sin(k / 3))
        glare = np.exp(-((np.arange(W)[None, :] - (k * 40) % W) ** 2) / (2 * 60 ** 2)) * 90
        img = img * gain + glare
        if k % 5 == 3:
            img = cv2.GaussianBlur(img, (0, 0), 2.0)
        img = np.clip(img + rnd.normal(0, 5, img.shape), 0, 255).astype(np.uint8)
        img = cv2.imdecode(cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])[1], 0)
        true = [cv2.transform(q.reshape(-1, 1, 2), M).reshape(-1, 2) for q in quads]
        yield img, true


def run(n: int = 24) -> dict:
    sid, single, drift, last = None, [], [], None
    for img, true in frames(n):
        lines = L.rapid_lines(img)
        for t, q in zip(LINES, true):
            c = q.mean(0)
            hit = [txt for quad, txt, _ in lines if np.linalg.norm(quad.mean(0) - c) < 0.6 * np.linalg.norm(q[3] - q[0])]
            single.append(bool(hit) and hit[0] == t)
        r = L.live_frame(sid, img)
        sid, last = r["session"], (r, true)
        for q in true:
            c, hgt = q.mean(0), np.linalg.norm(q[3] - q[0])
            near = [np.linalg.norm(np.mean(np.float32(x["quad"]), 0) - c) for x in r["lines"]]
            if near:
                drift.append(min(near) / hgt)
    L._POOL.submit(lambda: None).result()
    time.sleep(0.5)
    s = L.SESSIONS[sid]
    consensus = []
    for t, q in zip(LINES, last[1]):
        Hc = s.align(frames(n).__next__()[0])  # any frame aligns; the reference is fixed
        best = max(s.tracks, key=lambda tr: -np.linalg.norm(tr.quad.mean(0) - cv2.perspectiveTransform(q.reshape(-1, 1, 2), np.eye(3)).reshape(-1, 2).mean(0)), default=None)
        consensus.append(best is not None and best.text() == t)
    return {"id": "lens_live_eval", "frames": n, "single_frame_exact": round(float(np.mean(single)), 3),
            "session_texts": [tr.text() for tr in s.tracks], "drift_median_line_heights": round(float(np.median(drift)), 3),
            "drift_p90": round(float(np.quantile(drift, 0.9)), 3), "resets": s.resets, "thorough_readings": sum(bool(tr.deep) for tr in s.tracks)}


if __name__ == "__main__":
    res = run()
    res["consensus_exact"] = round(sum(t in res["session_texts"] for t in LINES) / len(LINES), 3)
    RESULT.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps(res, indent=1, ensure_ascii=False))
