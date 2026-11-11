"""Readers for other scripts compared (Round 93b); data/results/scripts_ocr_eval.json.

Scripts: Cyrillic (Russian), Arabic, Devanagari (Hindi), Japanese, Korean. Lines of real text from the held-out part
of the language identifier's Wikipedia samples (data/sources/langid), drawn by headless Chrome (which shapes Arabic and
Devanagari correctly; Pillow here cannot), then degraded like a photo (blur, noise, JPEG). Readers: Tesseract's script
model (what the Lens uses), PaddleOCR PP-OCRv4 recognisers through RapidOCR (paddle_ocr.py) with RapidOCR's line detector and on the line alone, and the local vision model.
Score: character error rate of the line, spaces ignored, case ignored."""
import json
import random
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

from . import paddle_ocr
from .ai_check import model_words
from .ocr import TESS
from .. import langid
from ..languages import ROOT

RESULT = ROOT / "data/results/scripts_ocr_eval.json"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SCRIPTS = {"Cyrillic": ("ru", "Arial"), "Arabic": ("ar", "Geeza Pro"), "Devanagari": ("hi", "Kohinoor Devanagari"),
           "Japanese": ("ja", "Hiragino Sans"), "Hangul": ("ko", "Apple SD Gothic Neo")}


def lines(code: str, n: int, rnd: random.Random, width: int = 24) -> list[str]:
    _, test = langid.split(code)
    text = " ".join(" ".join(test).split())
    out = []
    while len(out) < n:
        i = rnd.randrange(0, len(text) - width * 2)
        s = text[i:i + width * 2]
        s = s[s.find(" ") + 1:] if " " in s[:width // 2] else s
        s = s[:width].rsplit(" ", 1)[0] if " " in s[:width] else s[:width]
        if sum(c.isalpha() for c in s) >= 6:
            out.append(s.strip())
    return out


def draw(text: str, font: str, rtl: bool, tmp: Path, rnd: random.Random) -> np.ndarray:
    html = tmp / "l.html"
    html.write_text(f'<html><body style="margin:0;background:#fff"><div dir="{"rtl" if rtl else "ltr"}" style="font:36px \'{font}\';padding:20px;white-space:nowrap;display:inline-block">{text}</div></body></html>', encoding="utf-8")
    png = tmp / "l.png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={tmp / 'prof'}", "--window-size=1100,110", "--hide-scrollbars",
                    f"--screenshot={png}", html.as_uri()], capture_output=True, timeout=60)
    a = cv2.imread(str(png), cv2.IMREAD_GRAYSCALE)
    cols = np.where((a < 200).any(axis=0))[0]
    a = a[:, max(0, cols[0] - 20):cols[-1] + 20] if len(cols) else a
    a = cv2.GaussianBlur(a, (3, 3), rnd.uniform(0.3, 1.0))
    a = np.clip(a + np.random.default_rng(rnd.randint(0, 1 << 30)).normal(0, 6, a.shape), 0, 255).astype(np.uint8)
    return cv2.imdecode(cv2.imencode(".jpg", a, [cv2.IMWRITE_JPEG_QUALITY, 70])[1], cv2.IMREAD_GRAYSCALE)


def cer(truth: str, got: str) -> float:
    t, g = "".join(truth.lower().split()), "".join(got.lower().split())
    prev = list(range(len(g) + 1))
    for i, a in enumerate(t, 1):
        cur = [i]
        for j, b in enumerate(g, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a != b)))
        prev = cur
    return min(1.0, prev[-1] / max(len(t), 1))


def tesseract(img: np.ndarray, script: str) -> str:
    r = subprocess.run(["tesseract", "stdin", "stdout", "--tessdata-dir", str(TESS / "script"), "-l", script, "--psm", "7"],
                       input=cv2.imencode(".png", img)[1].tobytes(), capture_output=True, timeout=60)
    return r.stdout.decode("utf-8", "ignore").strip()


def run(n: int = 8, seed: int = 93) -> dict:
    rnd = random.Random(seed)
    out = {}
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        for script, (code, font) in SCRIPTS.items():
            rows = []
            for s in lines(code, n, rnd, 16 if code in ("ja", "ko") else 24):
                img = draw(s, font, script == "Arabic", tmp, rnd)
                m = model_words(img, timeout=60.0)
                rows.append({"truth": s, "tesseract": cer(s, tesseract(img, script)), "paddle_detected": cer(s, paddle_ocr.read(img, script)), "paddle_line": cer(s, paddle_ocr.read_line(img, script)),
                             "vision_model": cer(s, " ".join(m["words"]) if m else "")})
            out[script] = {k: round(float(np.mean([r[k] for r in rows])), 3) for k in ("tesseract", "paddle_detected", "paddle_line", "vision_model")}
            out[script]["lines"] = len(rows)
    return {"id": "scripts_ocr_eval", "results": out}


if __name__ == "__main__":
    r = run()
    RESULT.write_text(json.dumps(r, indent=1, ensure_ascii=False))
    print(json.dumps(r["results"], indent=1, ensure_ascii=False))
