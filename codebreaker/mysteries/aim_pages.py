"""PARKED (failed control, 12 of 52 exact): count dictionary entries on page images by flush-left lines."""
import json
import subprocess
import time

import cv2
import numpy as np

from ..languages import ROOT
from .aim_dictionary import CONTROL, LEAF_OFFSET, SOURCE, plain, similar

PAGES = SOURCE / "pages"
RESULT = ROOT / "data/results/aim_pages.json"
ID = "bub_gb_nST0CrtfIkEC"


def fetch(page: int) -> str:
    f = PAGES / f"n{page + LEAF_OFFSET}.jpg"
    if not f.exists() or f.stat().st_size < 20000:
        subprocess.run(["curl", "-sS", "-L", "-m", "60", "-A", "codebreaker-research/0.1", "-o", str(f), f"https://archive.org/download/{ID}/page/n{page + LEAF_OFFSET}.jpg"], check=False)
        time.sleep(1.0)
    return str(f)


def lines_in(ink: np.ndarray) -> list:
    """Text rows from the horizontal ink profile."""
    rows = ink.sum(axis=1) > max(3, ink.shape[1] * 0.012)
    out, start = [], None
    for y, on in enumerate(rows):
        if on and start is None:
            start = y
        if not on and start is not None:
            if y - start >= 9:
                out.append((start, y))
            start = None
    return out


def split_columns(ink: np.ndarray) -> tuple:
    """The central gutter or rule between the two columns."""
    w = ink.shape[1]
    prof = ink[int(ink.shape[0] * 0.1):int(ink.shape[0] * 0.92)].sum(axis=0).astype(float)
    mid = prof[int(w * 0.38):int(w * 0.62)]
    # A printed rule is the tallest narrow peak; a blank gutter is the lowest valley.
    h = ink.shape[0] * 0.82
    x = int(np.argmax(mid)) if mid.max() > 0.6 * h else int(np.argmin(np.convolve(mid, np.ones(9), "same")))
    return int(w * 0.38) + x


def entries(path: str, side: str) -> list:
    """Row spans of the flush-left lines of one column, top to bottom."""
    gray = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    ink = (cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1] > 0).astype(np.uint8)
    h = ink.shape[0]
    ink[int(h * 0.94):] = 0
    gut = split_columns(ink)
    col = ink[:, :gut - 6] if side == "L" else ink[:, gut + 6:]
    prof = col[int(h * 0.1):int(h * 0.92)].sum(axis=0)
    edges = np.where(prof > 0.04 * prof.max())[0]
    x0 = int(edges[0])
    col = col[:, x0:]
    width = col.shape[1]
    rows = lines_in(col)
    if rows and rows[0][0] < h * 0.1:
        rows = [r for r in rows if r[0] >= h * 0.075]
    out, ox = [], x0 + (0 if side == "L" else gut + 6)
    for a, b in rows:
        xs = np.where(col[a:b].sum(axis=0) > 0)[0]
        if len(xs) and xs[0] < width * 0.03:
            out.append((a, b))
    return [{"y0": a, "y1": b, "x0": ox, "width": width} for a, b in out]


def word_at(path: str, ent: dict) -> str:
    """OCR the head of one entry line."""
    gray = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    crop = gray[max(0, ent["y0"] - 4):ent["y1"] + 4, max(0, ent["x0"] - 6):ent["x0"] + int(ent["width"] * 0.62)]
    big = cv2.resize(crop, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    ok, buf = cv2.imencode(".png", big)
    r = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "7", "-l", "fra+eng"], input=buf.tobytes(), capture_output=True, timeout=30)
    text = r.stdout.decode("utf-8", "ignore").strip().split()
    return text[0].strip(",.;:") if text else ""


def lookup(page: int, side: str, n: int, span: int = 0) -> list:
    path = fetch(page)
    es = entries(path, side)
    return [word_at(path, es[i]) if 0 <= i < len(es) else "" for i in range(n - 1 - span, n + span)]


def control(pairs: list) -> dict:
    exact = near = 0
    rows = []
    for p, s, n, w in pairs:
        words = lookup(p, s, n, 1)
        e, c = similar(words[1], w) if words[1] else False, any(similar(x, w) for x in words if x)
        exact += e
        near += c
        rows.append([p, s, n, w, words])
    return {"pairs": len(pairs), "exact": exact, "within_1": near, "rows": rows}


def run() -> dict:
    d = json.loads(CONTROL.read_text())
    uniq = [list(x) for x in {tuple(p) for p in d["pairs"]}]
    out = {"id": "aim_pages", "control": control(sorted(uniq))}
    out["unsolved"] = {k: [{"ref": f"{p}{'a' if s == 'R' else ''}.{n}", "words": lookup(p, s, n, 1)} for p, s, n, _ in v] for k, v in d["unsolved"].items()}
    return out


if __name__ == "__main__":
    out = run()
    RESULT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    c = out["control"]
    print(c["pairs"], c["exact"], c["within_1"])
    for r in c["rows"]:
        if not any(similar(x, r[3]) for x in r[4] if x):
            print("MISS", r)
    for k, v in out["unsolved"].items():
        print(k)
        for w in v:
            print(" ", w)
