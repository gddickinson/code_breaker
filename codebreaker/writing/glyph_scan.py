"""Glyph scanner (Round 78): find signs in a photo or drawing and suggest what each one is.

Steps: grey image -> ink mask (Otsu threshold; the polarity with less ink is taken as ink) -> parts closed into whole
signs by a dilation scaled to the stroke size -> sign boxes, small specks dropped -> reading order (rows top to
bottom, left to right; a single tall column is read top to bottom) -> each crop normalised like the training images
-> the recogniser's top 5 with probabilities. A sign whose best probability is under the noise threshold measured in
evaluation is marked 'no confident match'. Results are suggestions for the user to confirm, never a silent reading."""
import base64
import json

import cv2
import numpy as np

from .glyph_model import RESULT, load, probabilities
from .glyph_render import classes, fit, prep


def decode_image(data_url: str) -> np.ndarray:
    raw = base64.b64decode(data_url.split(",", 1)[-1])
    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("The picture could not be read.")
    return img


MIN_CONTRAST = 35  # grey levels between ink and paper; paper texture alone stays below this


def ink_mask(gray: np.ndarray) -> np.ndarray:
    """Ink as 255. Empty if the darker and lighter classes differ by less than MIN_CONTRAST (texture, not ink)."""
    g = cv2.GaussianBlur(gray, (3, 3), 0)
    _, m = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    m = m if (m > 0).mean() < 0.5 else 255 - m
    if not m.any() or not (m == 0).any() or abs(float(g[m > 0].mean()) - float(g[m == 0].mean())) < MIN_CONTRAST:
        return np.zeros_like(m)
    return m


def boxes(mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Bounding boxes (x, y, w, h) of whole signs."""
    h, w = mask.shape
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    sizes = stats[1:, cv2.CC_STAT_HEIGHT]
    if not len(sizes):
        return []
    typical = float(np.median(sizes[sizes >= max(3, 0.01 * max(h, w))])) if (sizes >= max(3, 0.01 * max(h, w))).any() else 8.0
    k = max(1, int(typical * 0.12))
    keep = np.zeros_like(mask)  # specks are removed before parts are joined, so they cannot merge into a false sign
    for i, (x, y, bw, bh, area) in enumerate(stats[1:], 1):
        if max(bw, bh) >= 0.15 * typical and area >= 6:
            keep[lab == i] = 255
    closed = cv2.dilate(keep, np.ones((2 * k + 1, 2 * k + 1), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(closed, 8)
    out = []
    for x, y, bw, bh, area in stats[1:]:
        if bh < 0.25 * typical and bw < 0.25 * typical:
            continue  # specks
        out.append((int(x), int(y), int(bw), int(bh)))
    return out


def reading_order(bx: list[tuple]) -> list[tuple]:
    if not bx:
        return []
    hs = np.median([b[3] for b in bx])
    xs = [b[0] + b[2] / 2 for b in bx]
    if len(bx) > 2 and np.ptp(xs) < 0.6 * hs:  # one column
        return sorted(bx, key=lambda b: b[1])
    rows = []
    for b in sorted(bx, key=lambda b: b[1] + b[3] / 2):
        cy = b[1] + b[3] / 2
        if rows and abs(cy - rows[-1][0]) < 0.6 * hs:
            rows[-1][1].append(b)
            rows[-1][0] = np.mean([c[1] + c[3] / 2 for c in rows[-1][1]])
        else:
            rows.append([cy, [b]])
    return [b for _, r in rows for b in sorted(r, key=lambda b: b[0])]


def threshold() -> float:
    return json.loads(RESULT.read_text()).get("threshold", 0.2) if RESULT.exists() else 0.2


def scan(gray: np.ndarray, scripts: list[str] | None = None, top: int = 5) -> dict:
    if load() is None:
        raise RuntimeError("The glyph recogniser is not trained yet: run python -m codebreaker.writing.glyph_model.")
    mask = ink_mask(gray)
    order = reading_order(boxes(mask))[:300]
    g = cv2.GaussianBlur(gray, (3, 3), 0)
    ink_dark = mask.any() and g[mask > 0].mean() < g[mask == 0].mean()
    bright = 255 - gray if ink_dark else gray  # ink bright, as in training
    cls = classes()
    allowed = np.array([not scripts or c["script"] in scripts for c in cls])
    pad = lambda x, y, w, h: (max(0, x - 2), max(0, y - 2), x + w + 2, y + h + 2)
    spans = [pad(*b) for b in order]
    grey = np.stack([prep(fit(bright[y0:y1, x0:x1])) for x0, y0, x1, y1 in spans]) if order else np.zeros((0, 48, 48), np.uint8)
    hard = np.stack([prep(fit(mask[y0:y1, x0:x1])) for x0, y0, x1, y1 in spans]) if order else np.zeros((0, 48, 48), np.uint8)
    # two views of each sign, averaged: the grey crop keeps detail, the ink mask keeps faint thin lines (Round 78 page control)
    p = (probabilities(grey) + probabilities(hard)) / 2 if len(grey) else np.zeros((0, len(cls)))
    p = p * allowed
    p = p / np.maximum(p.sum(1, keepdims=True), 1e-9)
    thr, signs = threshold(), []
    for (x, y, w, h), row in zip(order, p):
        best = np.argsort(-row)[:top]
        cands = [{"sign": cls[k]["signs"][0], "also": cls[k]["signs"][1:], "script": cls[k]["script"], "values": cls[k]["values"],
                  "code": cls[k]["code"], "name": cls[k]["name"], "p": round(float(row[k]), 3)} for k in best]
        signs.append({"box": [x, y, w, h], "candidates": cands, "confident": bool(row[best[0]] >= thr)})
    votes = {}
    for s in signs:
        if s["confident"]:
            votes[s["candidates"][0]["script"]] = votes.get(s["candidates"][0]["script"], 0) + 1
    return {"size": [int(gray.shape[1]), int(gray.shape[0])], "signs": signs, "threshold": thr,
            "text": "".join(s["candidates"][0]["sign"] for s in signs if s["confident"]), "scripts": votes,
            "note": "Suggestions only: the recogniser was trained on font drawings, so worn carvings and handwriting may need a different choice from the list."}


def scan_data_url(data_url: str, scripts: list[str] | None = None) -> dict:
    return scan(decode_image(data_url), scripts)
