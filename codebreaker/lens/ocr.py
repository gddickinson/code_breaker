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

from ..languages import LANGS, ROOT

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


def variant(gray: np.ndarray, scale: float, kind: str) -> np.ndarray:
    """A copy prepared for Tesseract (Round 78b, measured on a photographed label): enlarged so small print reaches
    the letter size Tesseract wants, contrast evened out (CLAHE), and for 'adaptive' thresholded locally, which
    copes with glare and uneven light."""
    g = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC) if scale != 1 else gray
    g = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(g)
    if kind == "adaptive":
        g = cv2.adaptiveThreshold(cv2.GaussianBlur(g, (3, 3), 0), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41, 12)
    return g


def scale_for(gray: np.ndarray) -> float:
    """Pictures up to 1,600 px across are doubled (print in camera pictures is small); large scans are left alone."""
    return 2.0 if max(gray.shape) <= 1600 else 1.0


PASSES = (("clahe", 1.0, 3), ("adaptive", 1.0, 11), ("adaptive", 1.5, 11))  # (kind, extra scale, page mode)


def detect_script(gray: np.ndarray) -> tuple[str | None, float]:
    out = _run(gray, ["--tessdata-dir", str(TESS), "--psm", "0"])
    m, c = re.search(r"Script:\s*(\S+)", out), re.search(r"Script confidence:\s*([\d.]+)", out)
    if not m:
        return None, 0.0
    name = OSD_TO_MODEL.get(m.group(1), m.group(1))
    return (name if (TESS / "script" / f"{name}.traineddata").exists() else None), float(c.group(1)) if c else 0.0


def words(gray: np.ndarray, script: str, psm: int = 3) -> list[dict]:
    """Words with boxes (in the given image's pixels) and Tesseract's confidence 0-100."""
    tsv = _run(gray, ["--tessdata-dir", str(TESS / "script"), "-l", script, "--psm", str(psm), "-c", "tessedit_create_tsv=1"])
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
    return w["conf"] >= 60 and sum(c.isalnum() for c in t) >= max(1, 0.6 * len(t))  # 60: same recall as 50 on a photographed label, fewer junk words


MIN_LETTERS = 20  # below this, no language is named (Round 85, after the Lens named a wrong language from fragments)


def clean_for_language(words: list[dict]) -> str:
    """Only confidently read words of three or more letters: OCR fragments ('q t í') mislead the identifier."""
    def wordlike(t: str) -> bool:  # lower, upper or capitalised: misreads like 'PnPFR<' mix case inside a word
        core = re.sub(r"[^\w]", "", t)
        return bool(core) and (core.islower() or core.isupper() or (core[0].isupper() and core[1:].islower()))

    return " ".join(w["text"] for w in words if w["conf"] >= 60 and len(w["text"]) >= 3 and sum(c.isalpha() for c in w["text"]) >= 0.8 * len(w["text"]) and wordlike(w["text"]))


def language(text: str, script: str) -> dict:
    """The language among those with Wikipedia profiles (langid), in any script; named only with at least
    MIN_LETTERS letters and a calibrated probability of 0.8 or more, otherwise the script is reported."""
    from ..langid import detect as identify

    if sum(c.isalpha() for c in text) >= MIN_LETTERS:
        g = identify(text, 2)
        if g and g[0]["p"] >= 0.8:
            return {"code": g[0]["lang"], "name": g[0]["name"], "how": "character statistics", "p": g[0]["p"]}
        from ..langid_fasttext import detect as fasttext_detect  # optional second identifier (Round 93): same 0.8 bar

        f = fasttext_detect(text, 1)
        if f and f[0]["p"] >= 0.8:
            return {"code": f[0]["lang"], "name": f[0]["name"], "how": "fastText", "p": f[0]["p"]}
    return {"code": None, "name": SCRIPT_LANGS.get(script, "a " + script + "-script language"), "how": "script"}


def _overlap(a, b) -> float:
    ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    return ix * iy / max(1, min(a[2] * a[3], b[2] * b[3]))


def merge(passes: list[list[dict]]) -> list[dict]:
    """Words from several passes (boxes in original pixels): overlapping words are one word, read as in its most
    confident pass; a word kept if confident once (readable) or seen in two passes at confidence 30 or more."""
    out = []
    for ws in passes:
        for w in ws:
            same = next((o for o in out if _overlap(o["box"], w["box"]) > 0.5), None)
            if same is None:
                out.append({**w, "seen": 1, "best": w["conf"]})
                continue
            same["seen"] += 1
            if w["conf"] > same["best"]:
                same.update(text=w["text"], conf=w["conf"], best=w["conf"], line=w["line"])
    for o in out:
        if o["seen"] >= 2 and o["conf"] >= 30 and not readable(o):
            o["conf"] = max(o["conf"], 60.0)  # confirmed by a second pass
    return out


def _pass(gray: np.ndarray, script: str, kind: str, scale: float, psm: int) -> list[dict]:
    img = variant(gray, scale, kind)
    ws = words(img, script, psm)
    for w in ws:
        w["box"] = [round(v / scale) for v in w["box"]]
    return ws


_RAPID = None


def rapid():
    """RapidOCR (PaddleOCR detection and recognition models, installed with the app); None if unavailable."""
    global _RAPID
    if _RAPID is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _RAPID = RapidOCR()
        except Exception:
            _RAPID = False
    return _RAPID or None


def group_lines(ws: list[dict]) -> list[list[dict]]:
    """Words into lines by vertical overlap (a word joins a line when its centre lies inside the line's band), each
    line read left to right, lines top to bottom. Columns side by side end up on one line, as in reading order."""
    lines = []
    for w in sorted(ws, key=lambda w: w["box"][1] + w["box"][3] / 2):
        cy = w["box"][1] + w["box"][3] / 2
        line = next((l for l in lines if l["top"] - 0.15 * l["h"] <= cy <= l["top"] + 1.15 * l["h"]), None)
        if line is None:
            lines.append({"top": w["box"][1], "h": w["box"][3], "words": [w]})
        else:
            line["words"].append(w)
    return [sorted(l["words"], key=lambda w: w["box"][0]) for l in sorted(lines, key=lambda l: l["top"])]


def read(gray: np.ndarray, script: str | None = None, fast: bool = False, extra: list | None = None) -> dict:
    """OCR of a picture: script, words, lines, mean confidence and language. Latin script goes to ocr_deep: the fast
    RapidOCR reader for live frames, the thorough line-by-line comparison for photos. Other scripts: the candidate whose quick pass reads the most (total
    confidence of readable words), so a few confident junk words in a wrong script cannot win; stills then get three
    Tesseract passes merged, live frames one."""
    if not available():
        raise RuntimeError("The Tesseract language data is missing: see data/models/tessdata_fast/MANIFEST.md.")
    s = scale_for(gray)
    if script is None:
        osd, _ = detect_script(variant(gray, s, "clahe"))
        if osd in ("Latin", None) and rapid() is not None:
            from .ocr_deep import live_words

            probe = "".join(w["text"] for w in live_words(gray))
            alpha = [c for c in probe if c.isalpha()]
            if osd == "Latin" or (alpha and sum(c.isascii() for c in alpha) / len(alpha) >= 0.7):
                script = "Latin"  # detection unsure (it found nothing on a photographed label): RapidOCR's letters decide
    if script == "Latin" and rapid() is not None:  # two analysers (user's suggestion): fast for live, thorough for photos
        from .ocr_deep import live_words, photo_words

        ws = live_words(gray) if fast else photo_words(gray, extra)
        return _result(script, ws, [w for w in ws if readable(w)], [script])
    if script is None:
        cands = [osd] + (["Latin"] if osd != "Latin" else []) if osd else list(FALLBACK[:2] if fast else FALLBACK)
    else:
        cands = [script]
    best = None
    for sc in cands:
        ws = _pass(gray, sc, "clahe", s, 3)
        key = sum(w["conf"] for w in ws if readable(w))
        if best is None or key > best[0]:
            best = (key, sc, ws)
    _, script, first = best
    passes = [first] + ([] if fast else [_pass(gray, script, k, s * f, psm) for k, f, psm in PASSES[1:]])
    ws = merge(passes) if len(passes) > 1 else first
    return _result(script, ws, [w for w in ws if readable(w)], cands)


def _result(script: str, ws: list[dict], good: list[dict], tried: list[str]) -> dict:
    mean = float(np.mean([w["conf"] for w in good])) if good else 0.0
    text_lines = [" ".join(w["text"] for w in line) for line in group_lines(good)]
    return {"script": script, "words": ws, "lines": text_lines, "text": "\n".join(text_lines), "mean_conf": round(mean, 1),
            "language": language(clean_for_language(good), script) if good else None, "scripts_tried": tried, "known_languages": list(LANGS)}
