"""Controls for the vision model on hard live lines (Round 90c); data/results/lens_live_ai_eval.json.

Hard lines are made hard on purpose: one line of four words, drawn, then shrunk to a small text height, blurred and
lowered in contrast, as a line far from the camera looks. For each: the thorough OCR reading (ocr_deep.photo_words, as
the live session uses it), the model's reading, and the Lens check. Measured: word recall of each; how often the
model's line joins the vote (every word confirmed) and how often such a line is exactly right; on nonsense letter
strings, dictionary words the model invented. Hardness levels: text height 14, 10 and 8 pixels."""
import json
import random
import re

import cv2
import numpy as np

from . import ai_check as AC
from . import ocr
from .ai_eval import _vocab, photo
from ..languages import ROOT, corpus_text

RESULT = ROOT / "data/results/lens_live_ai_eval.json"


def hard(line: str, height: int, rnd: random.Random) -> np.ndarray:
    a = photo([line], rnd)
    s = height / 46.0  # the drawn font is about 46 pixels tall
    small = cv2.resize(a, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    small = (128 + (small.astype(np.float32) - 128) * rnd.uniform(0.4, 0.7)).clip(0, 255).astype(np.uint8)
    return cv2.resize(small, None, fx=1 / s, fy=1 / s, interpolation=cv2.INTER_LINEAR)


def one(img: np.ndarray, truth: list[str]) -> dict:
    from .ocr_deep import photo_words

    ws = [w for w in photo_words(cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)) if ocr.readable(w)]
    ocr_line = " ".join(w["text"] for w in sorted(ws, key=lambda w: w["box"][0]))
    m = AC.model_words(img, timeout=60.0) or {"words": [], "seconds": None}
    c = AC.check(m["words"], ocr_line.split(), [ocr_line])
    T = [AC.norm(w) for w in truth]
    rec = lambda words: sum(AC.norm(w) in T for w in words) / len(T)
    joins = bool(m["words"]) and not c["ai_only"]
    return {"ocr_recall": rec(ocr_line.split()), "ai_recall": rec(m["words"]), "joins_vote": joins,
            "joined_exact": joins and [AC.norm(w) for w in m["words"]] == T, "ai_only_words": len(c["ai_only"]),
            "invented": sum(AC.norm(w) not in T and AC.norm(w).upper() in _vocab() for w in m["words"]), "seconds": m["seconds"]}


def run(n: int = 6, seed: int = 90) -> dict:
    rnd = random.Random(seed)
    words = re.findall(r"[A-Za-z]{3,9}", corpus_text("en")[-300000:])
    out = {}
    for kind in ("real words", "nonsense"):
        for height in (14, 10, 8):
            rows = []
            for _ in range(n):
                ws = [rnd.choice(words) if kind == "real words" else "".join(rnd.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(rnd.randint(4, 7))) for _ in range(4)]
                rows.append(one(hard(" ".join(ws), height, rnd), ws))
            out[f"{kind}, text {height} px"] = {"lines": n, "ocr_recall": round(float(np.mean([r["ocr_recall"] for r in rows])), 3),
                                                 "ai_recall": round(float(np.mean([r["ai_recall"] for r in rows])), 3),
                                                 "joined_vote": sum(r["joins_vote"] for r in rows), "joined_and_exact": sum(r["joined_exact"] for r in rows),
                                                 "ai_only_words": sum(r["ai_only_words"] for r in rows), "invented_dictionary_words": sum(r["invented"] for r in rows),
                                                 "ai_seconds_mean": round(float(np.mean([r["seconds"] or 0 for r in rows])), 1)}
    return {"id": "lens_live_ai_eval", "model": AC.ai_local.status()["vision"], "results": out}


if __name__ == "__main__":
    r = run()
    RESULT.write_text(json.dumps(r, indent=1))
    print(json.dumps(r["results"], indent=1))
