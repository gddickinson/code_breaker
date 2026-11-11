"""Tesseract 'best' against 'fast' Latin script models (Round 93); data/results/tess_best_eval.json.

Model: script/Latin.traineddata from github.com/tesseract-ocr/tessdata_best (Apache-2.0, 101,402,885 bytes) in
data/models/tessdata_best (not committed), against the tessdata_fast model the Lens uses (89,384,811 bytes).
Measured through the Lens's own reading (ocr.read with the model folder switched) on the Round 90a photos of real
words and of nonsense strings and on the user's tin photo; and per line on the 128 transcribed Le Figaro ads
(character error rate of the transcription, as in Rounds 88b and 91). Time per picture."""
import json
import random
import re
import subprocess
import time

import cv2
import numpy as np

from . import ocr
from .ai_eval import TIN, TIN_WORDS, photo
from ..languages import ROOT, corpus_text

BEST = ROOT / "data/models/tessdata_best"
RESULT = ROOT / "data/results/tess_best_eval.json"
norm = lambda w: re.sub(r"[^\w]", "", w.lower())


def _recall(img, truth, folder) -> tuple[float, float]:
    old = ocr.TESS
    ocr.TESS = folder
    try:
        t = time.time()
        r = ocr.read(img, "Latin")
        sec = time.time() - t
    finally:
        ocr.TESS = old
    got = [norm(w["text"]) for w in r["words"] if ocr.readable(w)]
    pool, hit = list(got), 0
    for w in truth:
        if norm(w) in pool:
            pool.remove(norm(w))
            hit += 1
    return hit / max(len(truth), 1), sec


def _line(img, folder) -> str:
    big = cv2.copyMakeBorder(cv2.resize(img, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC), 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255)
    r = subprocess.run(["tesseract", "stdin", "stdout", "--tessdata-dir", str(folder / "script"), "-l", "Latin", "--psm", "7"],
                       input=cv2.imencode(".png", big)[1].tobytes(), capture_output=True, timeout=60)
    return r.stdout.decode("utf-8", "ignore")


def run(n: int = 6, seed: int = 90) -> dict:
    from ..mysteries import figaro_lineocr_data as D

    rnd = random.Random(seed)
    words = re.findall(r"[A-Za-z]{3,10}", corpus_text("en")[-300000:])
    sets = {"real words": [], "nonsense": []}
    for kind in sets:
        for _ in range(n):
            lines = [" ".join((rnd.choice(words) if kind == "real words" else "".join(rnd.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(rnd.randint(4, 8))))
                              for _ in range(4)) for _ in range(3)]
            sets[kind].append((photo(lines, rnd), " ".join(lines).split()))
    if TIN.exists():
        sets["tin photo"] = [(cv2.imread(str(TIN), cv2.IMREAD_GRAYSCALE), TIN_WORDS)]
    out = {}
    for kind, items in sets.items():
        for name, folder in (("fast", ocr.TESS), ("best", BEST)):
            rs = [_recall(img, t, folder) for img, t in items]
            out[f"{kind}, {name}"] = {"recall": round(float(np.mean([r[0] for r in rs])), 3), "seconds": round(float(np.mean([r[1] for r in rs])), 1)}
    truth = D.truth()
    cer = {"fast": [], "best": []}
    for name, t in sorted(truth.items()):
        lines = D.cut_lines(D.gray(D.IMAGES / name))
        for k, folder in (("fast", ocr.TESS), ("best", BEST)):
            cer[k].append(D.cer(t, "".join(_line(l, folder) for l in lines)))
    out["Le Figaro ads, mean character error"] = {k: round(float(np.mean(v)), 3) for k, v in cer.items()}
    out["Le Figaro ads, best better on"] = int(sum(b < f for f, b in zip(cer["fast"], cer["best"])))
    out["Le Figaro ads, fast better on"] = int(sum(f < b for f, b in zip(cer["fast"], cer["best"])))
    return {"id": "tess_best_eval", "results": out}


if __name__ == "__main__":
    r = run()
    RESULT.write_text(json.dumps(r, indent=1))
    print(json.dumps(r["results"], indent=1))
