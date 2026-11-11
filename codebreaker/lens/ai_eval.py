"""Controls for the vision model as a second reader (Round 90a); data/results/lens_ai_eval.json.

Positive: photos of real words (corpus words, three lines, drawn and degraded like a phone photo: perspective, blur,
noise, JPEG): recall of OCR, of the model, and precision of confirmed and AI-only words. Null 1, nonsense: the same
with random letter strings; a model word that is a dictionary word but not in the picture was invented (completion or
correction). Null 2, blank paper with noise: any word is invented. Timing per picture. Real: the user's tin photo
(data/lens_debug/tin_photo.jpg, local only) against its by-eye word list, when present."""
import json
import random
import re
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import ai_check as AC
from . import ocr
from ..languages import ROOT, corpus_text, model

RESULT = ROOT / "data/results/lens_ai_eval.json"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
TIN = ROOT / "data/lens_debug/tin_photo.jpg"  # the user's tin frame, kept locally (last_still.png is overwritten by later captures)
TIN_WORDS = ("ALTOIDS DISTRIBUTED BY MARS WRIGLEY CONFECTIONERY US LLC HACKETTSTOWN NJ USA Nutrition Facts Amount/serving Daily Value Total Fat "
             "Sodium Total Carb. Total Sugars Incl. Added Sugars Protein About servings per container Serving size mint Calories per serving "
             "MADE OF: SUGAR, GUM ARABIC, NATURAL FLAVORS (INCLUDING OIL OF PEPPERMINT), GELATIN. QUESTIONS? COMMENTS? CALL ALTOIDS.com").split()


def photo(lines: list[str], rnd: random.Random) -> np.ndarray:
    font = ImageFont.truetype(FONT, 46)
    w = max(int(font.getlength(l)) for l in lines) + 80
    im = Image.new("L", (w, 70 * len(lines) + 60), rnd.randint(200, 245))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        d.text((40, 30 + 70 * i), l, font=font, fill=rnd.randint(10, 60))
    a = np.asarray(im).copy()
    h, wd = a.shape
    j = lambda: rnd.uniform(-0.04, 0.04)
    src = np.float32([[0, 0], [wd, 0], [wd, h], [0, h]])
    dst = np.float32([[wd * j(), h * j()], [wd * (1 + j()), h * j()], [wd * (1 + j()), h * (1 + j())], [wd * j(), h * (1 + j())]])
    a = cv2.warpPerspective(a, cv2.getPerspectiveTransform(src, dst), (wd, h), borderValue=int(a[0, 0]))
    a = cv2.GaussianBlur(a, (5, 5), rnd.uniform(0.5, 1.5))
    a = np.clip(a + np.random.default_rng(rnd.randint(0, 1 << 30)).normal(0, 8, a.shape), 0, 255).astype(np.uint8)
    return cv2.imdecode(cv2.imencode(".jpg", a, [cv2.IMWRITE_JPEG_QUALITY, 60])[1], cv2.IMREAD_GRAYSCALE)


def _measure(img: np.ndarray, truth: list[str]) -> dict:
    t = time.time()
    o = ocr.read(img)
    ocr_s = time.time() - t
    readable = [w["text"] for w in o["words"] if ocr.readable(w)]
    m = AC.model_words(img)
    if m is None:
        return {"error": "no vision model"}
    lines = ["".join(w["text"] for w in line) for line in ocr.group_lines(o["words"])]
    c = AC.check(m["words"], [w["text"] for w in o["words"]], lines)
    T = {AC.norm(w) for w in truth}
    inn = lambda ws: sum(AC.norm(w) in T for w in ws)
    return {"truth": len(truth), "ocr_words": len(readable), "ocr_right": inn(readable), "ai_words": len(m["words"]), "ai_right": inn(m["words"]),
            "confirmed": len(c["confirmed"]), "confirmed_right": inn(c["confirmed"]), "ai_only": len(c["ai_only"]), "ai_only_right": inn(c["ai_only"]),
            "ai_invented_words": sum(AC.norm(w) not in T and AC.norm(w).upper() in _vocab() for w in m["words"]),
            "ocr_seconds": round(ocr_s, 1), "ai_seconds": m["seconds"]}


def _vocab() -> frozenset:
    return frozenset(str(w) for w in model("en")["words"][:20000])


def _sum(rows: list[dict]) -> dict:
    tot = lambda k: sum(r[k] for r in rows)
    return {"pictures": len(rows), "truth_words": tot("truth"),
            "ocr_recall": round(tot("ocr_right") / max(tot("truth"), 1), 3), "ai_recall": round(tot("ai_right") / max(tot("truth"), 1), 3),
            "confirmed_precision": round(tot("confirmed_right") / max(tot("confirmed"), 1), 3), "ai_only_precision": round(tot("ai_only_right") / max(tot("ai_only"), 1), 3),
            "ai_words": tot("ai_words"), "ai_invented_dictionary_words": tot("ai_invented_words"),
            "ocr_seconds_mean": round(float(np.mean([r["ocr_seconds"] for r in rows])), 1), "ai_seconds_mean": round(float(np.mean([r["ai_seconds"] for r in rows])), 1)}


def run(n: int = 6, seed: int = 90) -> dict:
    rnd = random.Random(seed)
    words = [w for w in re.findall(r"[A-Za-z]{3,10}", corpus_text("en")[-300000:])]
    out = {}
    pos = []
    for _ in range(n):
        lines = [" ".join(rnd.choice(words) for _ in range(4)) for _ in range(3)]
        pos.append(_measure(photo(lines, rnd), " ".join(lines).split()))
    out["real words"] = _sum(pos)
    non = []
    for _ in range(n):
        lines = [" ".join("".join(rnd.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(rnd.randint(4, 8))) for _ in range(4)) for _ in range(3)]
        non.append(_measure(photo(lines, rnd), " ".join(lines).split()))
    out["nonsense strings"] = _sum(non)
    blank = []
    for _ in range(3):
        img = photo([" "], rnd)
        blank.append(_measure(img, []))
    out["blank paper"] = {"pictures": len(blank), "ai_words": sum(r["ai_words"] for r in blank), "ocr_words": sum(r["ocr_words"] for r in blank)}
    if TIN.exists():
        out["tin photo (user's, by-eye words)"] = _sum([_measure(cv2.imread(str(TIN), cv2.IMREAD_GRAYSCALE), TIN_WORDS)])
    return {"id": "lens_ai_eval", "model": AC.ai_local.status()["vision"], "results": out}


if __name__ == "__main__":
    r = run()
    RESULT.write_text(json.dumps(r, indent=1))
    print(json.dumps(r["results"], indent=1))
