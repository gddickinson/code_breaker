"""Controls for pictures hidden in sound (Round 82): detection by carrier, level and method.

Carriers: white noise, synthetic birdsong (sound/synth.py) and a tone sweep. Hidden: the words of WORDS, one per
trial, at 0, -10, -15, -20 and -25 dB relative to the carrier. Methods: OCR of the spectrogram (the hidden word read
exactly) and the structure score (above the highest score of 20 clean carriers of the same kind). Clean carriers
also give the OCR false-alarm rate. The structure threshold is per carrier kind: no single threshold suits all audio."""
import json

import numpy as np

from ..languages import ROOT
from . import spectro_stego as G
from .synth import song

RESULT = ROOT / "data/results/spectro_eval.json"
WORDS = ["CODE", "SECRET", "HIDDEN", "MESSAGE", "CIPHER", "SIGNAL", "GARDEN", "WINTER"]
LEVELS = (0, -10, -15, -20, -25)


def carrier(kind: str, n: int, seed: int) -> np.ndarray:
    r = np.random.default_rng(seed)
    if kind == "noise":
        return r.normal(0, 0.1, n).astype(np.float32)
    if kind == "song":
        return np.resize(song(40, seed=seed)[0], n).astype(np.float32)
    t = np.arange(n) / G.SR
    return (0.3 * np.sin(2 * np.pi * (300 * t + 400 * t ** 2)) + r.normal(0, 0.02, n)).astype(np.float32)


def run(trials: int = 8) -> dict:
    n = len(G.hide(G.text_image("X"), seconds=4))
    out = {}
    for kind in ("noise", "song", "sweep"):
        clean = [carrier(kind, n, s) for s in range(20)]
        thr = max(G.structure(c) for c in clean)
        ocr_false = float(np.mean([G.detect(c)["finding"] for c in clean[:8]]))
        rows = {}
        for lvl in LEVELS:
            ocr = st = 0
            for t in range(trials):
                word = WORDS[t % len(WORDS)]
                x = G.mix(carrier(kind, n, 100 + t), G.hide(G.text_image(word), seconds=4, seed=t), lvl)
                d = G.detect(x)
                ocr += any(w["text"].upper() == word for w in d["words"])
                st += d["structure"] > thr
            rows[str(lvl)] = {"ocr_read_word": round(ocr / trials, 2), "structure_detected": round(st / trials, 2)}
        out[kind] = {"structure_threshold": round(thr, 3), "ocr_false_alarms_on_clean": ocr_false, "by_level_db": rows}
    return {"id": "spectro_eval", "trials": trials, "carriers": out}


if __name__ == "__main__":
    r = run()
    RESULT.write_text(json.dumps(r, indent=1))
    print(json.dumps(r, indent=1))
