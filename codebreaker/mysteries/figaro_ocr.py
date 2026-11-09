"""OCR for the scanned Le Figaro ads: two engines, keeping whichever reads each line better."""
import re
import subprocess
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np


@lru_cache(maxsize=1)
def _rapid():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def prepare(path: str, scale: float = 2.5) -> np.ndarray:
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"unreadable image {path}")
    big = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(big, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)


def cipher_lines(lines: list[str]) -> list[str]:
    """Keep lines that look like cipher text: long runs with few spaces and little punctuation."""
    out = []
    for raw in lines:
        s = raw.strip().strip(".,;:'\"|")
        compact = re.sub(r"\s+", "", s)
        alnum = re.findall(r"[A-Za-z0-9]", compact)
        if len(compact) < 10 or len(alnum) / len(compact) < 0.9:
            continue
        lower, digits = sum(c.islower() for c in alnum[1:]), sum(c.isdigit() for c in alnum)
        # Cipher lines are uniform: nearly all lower case, or digits. Mixed text is ad copy or a neighbour.
        if lower / max(len(alnum) - 1, 1) >= 0.85 or digits / len(alnum) >= 0.8:
            out.append(compact)
    return out


def tesseract_lines(img: np.ndarray) -> list[str]:
    ok, buf = cv2.imencode(".png", img)
    r = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "6", "-l", "eng"], input=buf.tobytes(), capture_output=True, timeout=60)
    return r.stdout.decode("utf-8", "ignore").splitlines()


def rapid_lines(img: np.ndarray) -> list[str]:
    result, _ = _rapid()(img)
    return [x[1] for x in result] if result else []


def read_ad(path: str) -> dict:
    """Return both readings and a merged text; each engine fills lines the other dropped."""
    img = prepare(path)
    tess, rapid = cipher_lines(tesseract_lines(img)), cipher_lines(rapid_lines(img))
    merged = list(rapid)
    for t in tess:
        key = re.sub(r"[^a-z]", "", t.lower())[:14]
        if not any(key and key in re.sub(r"[^a-z]", "", m.lower()) for m in merged):
            merged.insert(len(merged) if not merged else 0, t)
    # Keep document order by starting from whichever engine saw more lines when the other dropped some.
    base = tess if len(tess) > len(rapid) else rapid
    other = rapid if base is tess else tess
    final = []
    for line in base:
        k = re.sub(r"[^a-z0-9]", "", line.lower())
        best = max(other, key=lambda o: _overlap(k, re.sub(r"[^a-z0-9]", "", o.lower())), default=None)
        if best is not None and _overlap(k, re.sub(r"[^a-z0-9]", "", best.lower())) > 0.75:
            final.append(best if len(best) >= len(line) - 1 and base is tess else line)
        else:
            final.append(line)
    return {"tesseract": tess, "rapid": rapid, "text": "".join(final)}


def _overlap(a: str, b: str) -> float:
    from difflib import SequenceMatcher

    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def raw_read(path: str) -> dict:
    """Unfiltered lines from both engines, for attacks that can use short or abbreviated ads."""
    img = prepare(path)
    return {"tesseract": tesseract_lines(img), "rapid": rapid_lines(img)}
