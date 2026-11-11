"""The local vision model as a second transcriber for the Le Figaro scans (Round 91).

Each scan is read by the vision model (asked for every printed character, cipher groups included, with nothing
corrected or completed) and by RapidOCR, the best OCR engine on these scans (Round 88b). The two readings are aligned
(letters and digits, case ignored) and every character of the model's reading is marked agreed or disputed.
On ads already transcribed by eye, the character error rate (CER) of each reader is measured, and so is how far
agreement can be trusted: how often an agreed character is right, against a disputed one. Readings are cached in
data/results/figaro_vlm_readings.json. A reading here is never ciphertext: disputed characters go to a review queue,
and even agreed ones need a by-eye check before any analysis uses them."""
import json
from difflib import SequenceMatcher

from . import figaro_lineocr_data as D
from .. import ai_local
from ..languages import ROOT

CACHE = ROOT / "data/results/figaro_vlm_readings.json"
PROMPT = ("This is a scan of a small advertisement from the French newspaper Le Figaro, 1875-1900. Transcribe every character "
          "exactly as printed, line by line, including groups of letters or numbers that mean nothing (they are ciphers). "
          "Do not correct, translate, complete or explain anything.")


def _cache() -> dict:
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def vlm_read(name: str, cache: dict | None = None) -> str | None:
    cache = _cache() if cache is None else cache
    if name in cache:
        return cache[name]["text"]
    model = ai_local.status()["vision"]
    if not model:
        return None
    from ..lens.objects import model_grid
    import cv2

    img = cv2.imread(str(D.IMAGES / name))
    g, _, _ = model_grid(img)
    r = ai_local.generate(model, PROMPT, [cv2.imencode(".png", g)[1].tobytes()], timeout=120.0, num_predict=500)
    if r is None:
        return None
    cache[name] = {"text": r["text"], "model": model, "seconds": r["seconds"]}
    return r["text"]


def save(cache: dict) -> None:
    CACHE.write_text(json.dumps(cache, indent=0, ensure_ascii=False))


def agreement(a: str, b: str) -> list[bool]:
    """For each character of normalised a: is it matched by the same character in normalised b?"""
    a, b = D.norm(a), D.norm(b)
    flags = [False] * len(a)
    for blk in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for i in range(blk.a, blk.a + blk.size):
            flags[i] = True
    return flags


def marked(a: str, b: str) -> str:
    """The model's reading with disputed characters in brackets, for the review queue."""
    a = D.norm(a)
    f = agreement(a, b)
    out, i = [], 0
    while i < len(a):
        if f[i]:
            out.append(a[i])
            i += 1
        else:
            j = i
            while j < len(a) and not f[j]:
                j += 1
            out.append("[" + a[i:j] + "]")
            i = j
    return "".join(out)


def calibrate(truth: str, vlm: str, other: str) -> dict:
    """Agreed and disputed characters of the model's reading inside the stretch matching the transcription,
    each counted as right or wrong against the transcription."""
    v = D.norm(vlm)
    if not v:
        return {"agreed_right": 0, "agreed_wrong": 0, "disputed_right": 0, "disputed_wrong": 0}
    _, a0, a1 = D.local_align(truth, v)
    flags = agreement(vlm, other)
    right = [False] * len(v)
    for blk in SequenceMatcher(None, v[a0:a1], truth, autojunk=False).get_matching_blocks():
        for i in range(blk.a, blk.a + blk.size):
            right[a0 + i] = True
    c = {"agreed_right": 0, "agreed_wrong": 0, "disputed_right": 0, "disputed_wrong": 0}
    for i in range(a0, a1):
        c[("agreed_" if flags[i] else "disputed_") + ("right" if right[i] else "wrong")] += 1
    return c
