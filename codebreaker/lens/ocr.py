"""Printed text in pictures (Lens, Round 78b): script detection, word boxes and language identification.

Tesseract with the tessdata_fast models in data/models/tessdata_fast (126 languages and 37 script models, downloaded
with the user's permission; Apache 2.0). The script is found by Tesseract's orientation-and-script detection; when that
gives nothing (short or sparse text), the main script models are tried and the reading with the best mean word
confidence is kept. Within the Latin script the language is identified with the app's own models, so only languages
the app knows are named; other scripts are named by script."""
import re
import subprocess

import cv2
import numpy as np

from ..languages import LANGS, ROOT, detect, score
from ..text import letters

TESS = ROOT / "data/models/tessdata_fast"
FALLBACK = ("Latin", "Cyrillic", "Greek", "Arabic", "Hebrew", "Devanagari", "HanS", "Japanese", "Hangul")
OSD_TO_MODEL = {"Han": "HanS", "Katakana": "Japanese", "Hiragana": "Japanese", "Korean": "Hangul"}
SCRIPT_LANGS = {"Cyrillic": "Russian, Ukrainian, Bulgarian, Serbian or another Cyrillic language", "Greek": "Greek", "Arabic": "Arabic, Persian or Urdu",
                "Hebrew": "Hebrew or Yiddish", "Devanagari": "Hindi, Marathi, Nepali or Sanskrit", "HanS": "Chinese (simplified)",
                "HanT": "Chinese (traditional)", "Japanese": "Japanese", "Hangul": "Korean", "Thai": "Thai", "Georgian": "Georgian", "Armenian": "Armenian",
                "Ethiopic": "Amharic or another Ethiopic language", "Fraktur": "German in Fraktur type"}


def available() -> bool:
    return (TESS / "script" / "Latin.traineddata").exists()


def _png(gray: np.ndarray) -> bytes:
    ok, enc = cv2.imencode(".png", gray)
    return enc.tobytes()


def _run(gray: np.ndarray, args: list[str]) -> str:
    r = subprocess.run(["tesseract", "stdin", "stdout", *args], input=_png(gray), capture_output=True, timeout=60)
    return r.stdout.decode("utf-8", "ignore")


def prepare(gray: np.ndarray) -> tuple[np.ndarray, float]:
    """Upscale small pictures (Tesseract wants letters of about 30 px); returns the image and the scale used."""
    s = 1.0
    if max(gray.shape) < 1400:
        s = min(3.0, 1400 / max(gray.shape))
        gray = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
    return gray, s


def detect_script(gray: np.ndarray) -> tuple[str | None, float]:
    out = _run(gray, ["--tessdata-dir", str(TESS), "--psm", "0"])
    m, c = re.search(r"Script:\s*(\S+)", out), re.search(r"Script confidence:\s*([\d.]+)", out)
    if not m:
        return None, 0.0
    name = OSD_TO_MODEL.get(m.group(1), m.group(1))
    return (name if (TESS / "script" / f"{name}.traineddata").exists() else None), float(c.group(1)) if c else 0.0


def words(gray: np.ndarray, script: str) -> list[dict]:
    """Words with boxes (in the given image's pixels) and Tesseract's confidence 0-100."""
    tsv = _run(gray, ["--tessdata-dir", str(TESS / "script"), "-l", script, "--psm", "3", "-c", "tessedit_create_tsv=1"])
    out = []
    for line in tsv.splitlines()[1:]:
        f = line.split("\t")
        if len(f) < 12 or not f[11].strip():
            continue
        conf = float(f[10])
        if conf < 0:
            continue
        out.append({"text": f[11].strip(), "box": [int(f[6]), int(f[7]), int(f[8]), int(f[9])], "conf": round(conf, 1),
                    "line": f"{f[2]}.{f[3]}.{f[4]}"})
    return out


def readable(w: dict) -> bool:
    """A word worth reading: confident, and mostly letters or digits (pattern noise from codes and pictures is not)."""
    t = w["text"]
    return w["conf"] >= 50 and sum(c.isalnum() for c in t) >= max(1, 0.6 * len(t))


def language(text: str, script: str) -> dict:
    """The language for Latin-script text among the app's languages (only if the text reads as one), else the script."""
    if script == "Latin" and len(letters(text)) >= 12:
        best = detect(text)[0]
        if score(letters(text), best["lang"]) > -5.2:
            return {"code": best["lang"], "name": best["name"], "how": "letter statistics"}
        return {"code": None, "name": "a Latin-script language the app has no model for", "how": "letter statistics"}
    return {"code": None, "name": SCRIPT_LANGS.get(script, script), "how": "script"}


def read(gray: np.ndarray, script: str | None = None, fast: bool = False) -> dict:
    """OCR of a picture: script, words, lines, mean confidence and language."""
    if not available():
        raise RuntimeError("The Tesseract language data is missing: see data/models/tessdata_fast/MANIFEST.md.")
    big, s = prepare(gray)
    tried = []
    if script is None:
        script, sconf = detect_script(big)
        tried = [script] if script else []
    cands = [script] if script else list(FALLBACK[:2] if fast else FALLBACK)
    best = None
    for sc in cands:
        ws = words(big, sc)
        good = [w for w in ws if w["conf"] >= 40 and re.search(r"\w", w["text"])]
        mean = float(np.mean([w["conf"] for w in good])) if good else 0.0
        key = mean * min(1.0, len(good) / 3)
        if best is None or key > best[0]:
            best = (key, sc, ws, mean)
    _, script, ws, mean = best
    for w in ws:
        w["box"] = [round(v / s) for v in w["box"]]
    lines = {}
    for w in ws:
        if readable(w):
            lines.setdefault(w["line"], []).append(w["text"])
    text_lines = [" ".join(v) for v in lines.values()]
    text = "\n".join(text_lines)
    return {"script": script, "words": ws, "lines": text_lines, "text": text, "mean_conf": round(mean, 1),
            "language": language(text, script) if text.strip() else None, "scripts_tried": tried or cands, "known_languages": list(LANGS)}
