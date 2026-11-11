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


JOIN = 0.08  # join radius as a share of the typical part height; chosen on the page control with tight gaps (Round 78b)


def boxes(mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Bounding boxes (x, y, w, h) of whole signs."""
    h, w = mask.shape
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    sizes = stats[1:, cv2.CC_STAT_HEIGHT]
    if not len(sizes):
        return []
    typical = float(np.median(sizes[sizes >= max(3, 0.01 * max(h, w))])) if (sizes >= max(3, 0.01 * max(h, w))).any() else 8.0
    k = max(1, int(typical * JOIN))
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


def _runs(on: np.ndarray) -> list[tuple[int, int]]:
    """(start, end) of each run of True."""
    d = np.diff(np.concatenate([[0], on.astype(np.int8), [0]]))
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


def projection_boxes(mask: np.ndarray) -> list[tuple[int, int, int, int]] | None:
    """Rows of ink, then cuts at empty columns within each row. Gaps inside a sign (Old Persian wedges) and between
    signs are told apart by splitting the gap widths in two (Otsu) when they differ enough; otherwise every gap
    separates signs. None for layouts this does not suit (a single tall column, as in vertical writing)."""
    m = mask > 0
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n <= 1:
        return []
    th = float(np.median(st[1:, cv2.CC_STAT_HEIGHT]))
    smear = cv2.dilate(mask, np.ones((1, max(3, int(2 * th))), np.uint8))  # sideways only: tilted rows stay apart
    ln, llab, lst, _ = cv2.connectedComponentsWithStats(smear, 8)
    lines = [(int(lst[i, cv2.CC_STAT_TOP]), i) for i in range(1, ln) if lst[i, cv2.CC_STAT_HEIGHT] >= 3]
    rows = []
    out = []
    for _, li in sorted(lines):
        x, y, w, h = (int(v) for v in lst[li, :4])
        band = m[y:y + h, x:x + w] & (llab[y:y + h, x:x + w] == li)
        rows.append((y, y + h))
        y0 = y
        cols = band.sum(0) > 0
        segs = [c for c in _runs(cols)]
        if len(segs) > 1:
            gaps = np.array([segs[i + 1][0] - segs[i][1] for i in range(len(segs) - 1)], float)
            if gaps.max() >= 1.8 * max(gaps.min(), 1):
                vals = np.sort(gaps)
                best, thr = -1.0, vals[-1]
                for t in np.unique(vals)[1:]:  # Otsu on the gap widths
                    a, b = vals[vals < t], vals[vals >= t]
                    v = len(a) * len(b) * (a.mean() - b.mean()) ** 2
                    if v > best:
                        best, thr = v, t
                cut = gaps >= min(thr, 0.22 * h)  # a gap of a fifth of the sign height always separates signs
            else:
                cut = np.ones(len(gaps), bool)
            groups, cur = [], [segs[0]]
            for g, sg, c in zip(gaps, segs[1:], cut):
                if c:
                    groups.append(cur)
                    cur = [sg]
                else:
                    cur.append(sg)
            groups.append(cur)
        else:
            groups = [segs]
        for gr in groups:
            x0, x1 = gr[0][0], gr[-1][1]
            ys = np.where(band[:, x0:x1].any(1))[0]
            out.append((int(x + x0), int(y0 + ys.min()), int(x1 - x0), int(ys.max() - ys.min() + 1)))
    hs = np.median([b[3] for b in out])
    if len(rows) == 1 and (rows[0][1] - rows[0][0]) > 3 * np.median([b[2] for b in out]) and len(out) < 3:
        return None  # one tall column: leave it to the joining method
    return [b for b in out if max(b[2], b[3]) >= 0.2 * hs]


def merge_fragments(bx: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    """Signs made of separate strokes (Old Persian wedges) come out of a small join radius in pieces: a box much
    smaller than the typical sign joins its nearest neighbour when the union stays sign-sized (Round 78b)."""
    bx = list(bx)
    for _ in range(4 * len(bx)):
        if len(bx) < 2:
            break
        hs, ws = np.median([b[3] for b in bx]), np.median([b[2] for b in bx])
        big = max(np.percentile([b[3] for b in bx], 75), hs)
        bigw = max(np.percentile([b[2] for b in bx], 75), ws)
        small = [i for i, b in enumerate(bx) if b[3] < 0.6 * big and b[2] < 0.6 * bigw]
        merged = False
        for i in small:
            x, y, w, h = bx[i]
            cx, cy = x + w / 2, y + h / 2
            best, bd = None, None
            for j, (x2, y2, w2, h2) in enumerate(bx):
                if j == i:
                    continue
                ux, uy = min(x, x2), min(y, y2)
                uw, uh = max(x + w, x2 + w2) - ux, max(y + h, y2 + h2) - uy
                if uw > 1.25 * bigw or uh > 1.25 * big:
                    continue
                d = (cx - x2 - w2 / 2) ** 2 + (cy - y2 - h2 / 2) ** 2
                if bd is None or d < bd:
                    best, bd = (j, (ux, uy, uw, uh)), d
            if best:
                j, u = best
                bx = [b for k, b in enumerate(bx) if k not in (i, j)] + [u]
                merged = True
                break
        if not merged:
            break
    return bx


def split_wide(bx: list[tuple[int, int, int, int]], mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Two signs joined across a tight gap make a box much wider than typical: cut it at its emptiest column gap."""
    if len(bx) < 3:
        return bx
    mw = np.median([b[2] for b in bx])
    out = []
    for x, y, w, h in bx:
        if w > 1.7 * mw:
            cols = (mask[y:y + h, x:x + w] > 0).sum(0)
            lo, hi = int(0.25 * w), int(0.75 * w)
            if hi > lo and cols[lo:hi].min() == 0:
                zero = np.where(cols[lo:hi] == 0)[0] + lo
                cut = int(zero[len(zero) // 2])
                out += [(x, y, cut, h), (x + cut, y, w - cut, h)]
                continue
        out.append((x, y, w, h))
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


def segment(mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Sign boxes in reading order: rows cut at empty columns, or parts joined, whichever suits the page."""
    pb = projection_boxes(mask)
    proj = merge_fragments(pb) if pb is not None else []
    join = split_wide(merge_fragments(boxes(mask)), mask)
    # each method fails where the other does not (tight gaps merge signs in rows; signs on a shared stem have no empty
    # column): joining wins only with more boxes of full height, since signs merged side by side keep their height
    # while a sign broken into strokes (Old Persian wedges) does not
    med_h = lambda bs: float(np.median([b[3] for b in bs])) if bs else 0.0
    use_join = len(join) > len(proj) and med_h(join) >= 0.85 * med_h(proj)
    return reading_order(join if use_join else proj)[:300]


def threshold() -> float:
    return json.loads(RESULT.read_text()).get("threshold", 0.2) if RESULT.exists() else 0.2


def scan(gray: np.ndarray, scripts: list[str] | None = None, top: int = 5) -> dict:
    if load() is None:
        raise RuntimeError("The glyph recogniser is not trained yet: run python -m codebreaker.writing.glyph_model.")
    mask = ink_mask(gray)
    order = segment(mask)
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
