"""Handwriting readers compared (Round 93c); data/results/handwriting_eval.json.

No real handwritten lines with known text are in the project, so the test uses the handwriting-style fonts macOS ships
(Bradley Hand, Savoye, Snell Roundhand, Apple Chancery, Chalkboard, Zapfino): a weak stand-in for real hands, much
more regular. Lines of four real English words and of four nonsense letter strings (cipher-like), slightly rotated,
blurred, noisy, JPEG. Readers: Tesseract (Latin script model, one line), TrOCR (handwriting.py) and the local vision
model. Score: character error rate, case and spaces ignored; on nonsense also the dictionary words a reader wrote that
were not there."""
import json
import random
import re

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import handwriting
from .ai_check import model_words
from .ai_eval import _vocab
from .scripts_ocr_eval import cer, tesseract
from ..languages import ROOT, corpus_text

RESULT = ROOT / "data/results/handwriting_eval.json"
FONTS = ["Bradley Hand Bold.ttf", "Savoye LET.ttc", "SnellRoundhand.ttc", "Apple Chancery.ttf", "Chalkboard.ttc", "Zapfino.ttf"]


def draw(text: str, font: str, rnd: random.Random) -> np.ndarray:
    f = ImageFont.truetype(f"/System/Library/Fonts/Supplemental/{font}", 46)
    w = int(f.getlength(text)) + 60
    im = Image.new("L", (w, 160), 255)
    ImageDraw.Draw(im).text((30, 40), text, font=f, fill=rnd.randint(10, 70))
    a = np.asarray(im.rotate(rnd.uniform(-1.5, 1.5), fillcolor=255)).copy()
    rows = np.where((a < 160).any(axis=1))[0]
    a = a[max(0, rows[0] - 8):rows[-1] + 8] if len(rows) else a
    a = cv2.GaussianBlur(a, (3, 3), rnd.uniform(0.3, 0.9))
    a = np.clip(a + np.random.default_rng(rnd.randint(0, 1 << 30)).normal(0, 6, a.shape), 0, 255).astype(np.uint8)
    return cv2.imdecode(cv2.imencode(".jpg", a, [cv2.IMWRITE_JPEG_QUALITY, 70])[1], cv2.IMREAD_GRAYSCALE)


def invented(truth: str, got: str) -> int:
    t = {w.upper() for w in truth.split()}
    return sum(w.upper() not in t and w.upper() in _vocab() and len(w) >= 3 for w in re.findall(r"[A-Za-z]+", got))


def run(per_font: int = 3, seed: int = 93) -> dict:
    rnd = random.Random(seed)
    words = re.findall(r"[a-z]{3,9}", corpus_text("en")[-300000:].lower())
    out = {}
    for kind in ("real words", "nonsense"):
        rows = []
        for font in FONTS:
            for _ in range(per_font):
                s = " ".join(rnd.choice(words) if kind == "real words" else "".join(rnd.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(rnd.randint(4, 7))) for _ in range(4))
                img = draw(s, font, rnd)
                m = model_words(img, timeout=60.0)
                got = {"tesseract": tesseract(img, "Latin"), "trocr": handwriting.read_line(img), "vision_model": " ".join(m["words"]) if m else ""}
                rows.append({"font": font, **{k: cer(s, v) for k, v in got.items()}, **{f"{k}_invented": invented(s, v) for k, v in got.items()}})
        res = {k: round(float(np.mean([r[k] for r in rows])), 3) for k in ("tesseract", "trocr", "vision_model")}
        if kind == "nonsense":
            res.update({f"{k} dictionary words invented": sum(r[f"{k}_invented"] for r in rows) for k in ("tesseract", "trocr", "vision_model")})
        res["by font"] = {f: {k: round(float(np.mean([r[k] for r in rows if r["font"] == f])), 2) for k in ("tesseract", "trocr", "vision_model")} for f in FONTS}
        res["lines"] = len(rows)
        out[kind] = res
    return {"id": "handwriting_eval", "caveat": "font handwriting, not real hands", "results": out}


if __name__ == "__main__":
    r = run()
    RESULT.write_text(json.dumps(r, indent=1))
    print(json.dumps(r["results"], indent=1))
