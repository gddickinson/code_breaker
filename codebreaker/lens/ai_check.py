"""The local vision model as a checked second reader for Lens photos (Round 90a).

The model is asked to transcribe the picture exactly. Its words are then checked against the OCR evidence: every OCR
word, readable or not, and each OCR line with its spaces removed. A model word counts as confirmed when an OCR word
is within a small edit distance of it (one edit, or a quarter of its length) or it appears inside an OCR line's
letters; otherwise it is shown labelled as AI only. Vision models tend to complete, correct and invent text, so an
unconfirmed word is a suggestion, never a reading (controls in ai_eval.py)."""
import re

import cv2
import numpy as np

from .. import ai_local

PROMPT = ("Transcribe all text visible in this image exactly as written, line by line. Do not add, translate, correct "
          "or describe anything. If there is no text, answer NONE.")


def norm(w: str) -> str:
    return re.sub(r"[^\w]", "", w.lower())


def edit(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def model_words(gray: np.ndarray, model: str | None = None, timeout: float = 120.0) -> dict | None:
    st = ai_local.status()
    model = model or st["vision"]
    if not model:
        return None
    ok, png = cv2.imencode(".png", gray)
    r = ai_local.generate(model, PROMPT, [png.tobytes()], timeout=timeout)
    if r is None:
        return None
    text = "" if r["text"].strip().upper().startswith("NONE") else r["text"]
    return {"model": model, "seconds": r["seconds"], "text": text, "words": [w for w in text.split() if norm(w)]}


def check(ai_words: list[str], ocr_words: list[str], ocr_lines: list[str]) -> dict:
    """Split the model's words into confirmed (OCR letters agree) and AI only."""
    pool = [norm(w) for w in ocr_words if norm(w)]
    lines = [norm(l) for l in ocr_lines]
    confirmed, ai_only = [], []
    for w in ai_words:
        n = norm(w)
        tol = max(1, len(n) // 4)
        ok = any(abs(len(n) - len(p)) <= tol and edit(n, p) <= tol for p in pool) or (len(n) >= 3 and any(n in l for l in lines))
        (confirmed if ok else ai_only).append(w)
    return {"confirmed": confirmed, "ai_only": ai_only}


def second_reader(gray: np.ndarray, ocr_result: dict) -> dict:
    """What the Lens shows: the mode that ran, the model's words split by evidence, and timing."""
    st = ai_local.status()
    if not st["vision"]:
        return {"mode": "own algorithms only", "note": st["note"]}
    m = model_words(gray)
    if m is None:
        return {"mode": "own algorithms only", "note": f"{st['vision']} did not answer in time."}
    words = [w["text"] for w in ocr_result["words"]]
    from .ocr import group_lines

    lines = ["".join(w["text"] for w in line) for line in group_lines(ocr_result["words"])]
    c = check(m["words"], words, lines)
    return {"mode": f"own algorithms + local {m['model']}", "seconds": m["seconds"], **c,
            "note": "Confirmed words agree with the OCR letters; AI-only words are the model's suggestion and may be invented."}
