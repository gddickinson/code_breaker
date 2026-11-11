"""End-to-end control for the glyph scanner (Round 78): synthetic pages with known signs.

Each page is a few rows of signs chosen at random from one script, drawn dark on textured light paper, with a slight
rotation, blur and noise. The scanner must find each sign (a found box overlapping the true box), in reading order,
and name it (top 1 and top 5). Pages of pure paper texture with no signs give the false-detection rate."""
import json

import cv2
import numpy as np

from ..languages import ROOT
from .glyph_render import classes, raw
from .glyph_scan import scan

RESULT = ROOT / "data/results/glyph_scan_eval.json"


def page(script: str, rnd: np.random.Generator, rows: int = 2, per_row: int = 6, size: int = 64) -> tuple[np.ndarray, list]:
    pool = [k for k, c in enumerate(classes()) if c["script"] == script]
    gap = size // 3
    h, w = rows * (size + gap) + gap, per_row * (size + gap) + gap
    paper = np.clip(rnd.normal(215, 12, (h, w)) + cv2.GaussianBlur(rnd.normal(0, 25, (h, w)), (0, 0), 6), 0, 255)
    truth = []
    for r in range(rows):
        for c in range(per_row):
            k = int(rnd.choice(pool))
            a = raw(classes()[k]["signs"][0], script).astype(np.float32)
            s = size / max(a.shape)
            a = cv2.resize(a, (max(1, int(a.shape[1] * s)), max(1, int(a.shape[0] * s))))
            y, x = gap + r * (size + gap) + (size - a.shape[0]) // 2, gap + c * (size + gap) + (size - a.shape[1]) // 2
            paper[y:y + a.shape[0], x:x + a.shape[1]] -= a * 0.7
            truth.append((k, (x, y, a.shape[1], a.shape[0])))
    m = cv2.getRotationMatrix2D((w / 2, h / 2), float(rnd.uniform(-2, 2)), 1.0)
    img = cv2.warpAffine(np.clip(paper, 0, 255), m, (w, h), borderValue=215)
    img = cv2.GaussianBlur(img, (0, 0), 0.7) + rnd.normal(0, 6, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8), truth


def _overlap(a, b) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    return ix * iy / max(1, min(aw * ah, bw * bh))


def run(pages_per_script: int = 6, seed: int = 78) -> dict:
    rnd, cls, out = np.random.default_rng(seed), classes(), {}
    for script in sorted({c["script"] for c in cls}):
        found = top1 = top5 = total = extra = ordered = 0
        for _ in range(pages_per_script):
            img, truth = page(script, rnd)
            res = scan(img, [script])
            got = [s["box"] for s in res["signs"]]
            used, seq = set(), []
            for k, tb in truth:
                total += 1
                j = next((i for i, b in enumerate(got) if i not in used and _overlap(b, tb) > 0.5), None)
                if j is None:
                    continue
                used.add(j)
                seq.append(j)
                found += 1
                names = ["".join([c["sign"]] + c["also"]) for c in res["signs"][j]["candidates"]]
                want = "".join(cls[k]["signs"])
                top1 += names[0] == want
                top5 += want in names
            extra += len(got) - len(used)
            ordered += seq == sorted(seq)
        out[script] = {"signs": total, "found": round(found / total, 3), "top1": round(top1 / total, 3), "top5": round(top5 / total, 3),
                       "extra_boxes_per_page": round(extra / pages_per_script, 2), "pages_in_order": round(ordered / pages_per_script, 3)}
    blank = [len(scan(np.clip(rnd.normal(215, 12, (180, 420)) + cv2.GaussianBlur(rnd.normal(0, 25, (180, 420)), (0, 0), 6), 0, 255).astype(np.uint8))["signs"])
             for _ in range(10)]
    return {"id": "glyph_scan_eval", "by_script": out, "blank_pages_boxes": blank}


if __name__ == "__main__":
    res = run()
    RESULT.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
