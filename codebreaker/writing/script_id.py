"""Which script a set of signs belongs to (Round 79).

Each sign's recogniser output is summed per script (its probability of being any sign of that script); each sign then
votes for its best script, weighted by that probability, and the vote shares rank the scripts. (Multiplying the
probabilities, the first version, let a few badly distorted signs outvote the rest once the model had learned
photographs.) A set is called 'no known script' when fewer than KNOWN_SHARE of its signs are recognised confidently.

Control (evaluate): synthetic pages of each script with 1, 2, 4, 8 and 12 signs, clean and with the 'unseen'
distortions (perspective, uneven light, motion blur, JPEG), and two kinds of non-script input: random blob shapes and
Latin letters drawn in an ordinary font, which should come back as no known script."""
import json

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..languages import ROOT
from .glyph_model import probabilities
from .glyph_render import classes, distort, fit, prep, raw, unseen
from .glyph_scan import threshold

RESULT = ROOT / "data/results/script_id.json"


def script_masses(p: np.ndarray) -> tuple[list[str], np.ndarray]:
    scripts = sorted({c["script"] for c in classes()})
    idx = np.array([scripts.index(c["script"]) for c in classes()])
    mass = np.zeros((p.shape[0], len(scripts)))
    for j in range(len(scripts)):
        mass[:, j] = p[:, idx == j].sum(1)
    return scripts, mass


KNOWN_SHARE = 0.35  # share of signs recognised confidently before a script is named; chosen on unseen-distortion
                   # sets against blob and Latin-letter controls (Round 79): right 64%, wrong 2.8%, Latin named 10%


def identify(p: np.ndarray, thr: float | None = None) -> dict:
    """p: recogniser probabilities, one row per sign. Each sign votes for its most likely script, weighted by that
    script's probability (robust to a few badly distorted signs, which outvoted the rest when probabilities were
    multiplied); a script is named only if at least KNOWN_SHARE of the signs are recognised confidently."""
    thr = threshold() if thr is None else thr
    if len(p) == 0:
        return {"script": None, "ranking": [], "signs": 0, "verdict": "no signs"}
    scripts, mass = script_masses(p)
    tally = np.bincount(mass.argmax(1), weights=mass.max(1), minlength=len(scripts))
    share = tally / max(tally.sum(), 1e-9)
    order = np.argsort(-share)
    confident = float((p.max(1) >= thr).mean())
    best = scripts[order[0]]
    known = confident >= KNOWN_SHARE
    return {"script": best if known else None, "posterior": round(float(share[order[0]]), 3), "confident_share": round(confident, 2),
            "ranking": [{"script": scripts[i], "p": round(float(share[i]), 3)} for i in order[:4]], "signs": int(len(p)),
            "verdict": best if known else "no known script (too few signs recognised confidently)"}


def _sign(k: int, rnd: np.random.Generator, hard: bool) -> np.ndarray:
    a = raw(classes()[k]["signs"][0], classes()[k]["script"])
    return prep(unseen(a, rnd)) if hard else prep(distort(a, rnd))  # 'clean' = a mild, training-style copy, as a good scan


def _blob(rnd: np.random.Generator) -> np.ndarray:
    img = np.zeros((96, 96), np.uint8)
    for _ in range(int(rnd.integers(2, 5))):
        pts = rnd.integers(10, 86, (int(rnd.integers(3, 7)), 2)).astype(np.int32)
        cv2.polylines(img, [pts], bool(rnd.random() < 0.5), 255, int(rnd.integers(3, 8)))
    return prep(fit(img))


def _latin(rnd: np.random.Generator) -> np.ndarray:
    im = Image.new("L", (120, 120), 0)
    ImageDraw.Draw(im).text((20, 10), chr(int(rnd.integers(65, 91))), font=ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 80), fill=255)
    a = np.asarray(im)
    ys, xs = np.nonzero(a)
    return prep(fit(a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]))


def evaluate(trials: int = 30, sizes=(1, 2, 4, 8, 12), seed: int = 79) -> dict:
    rnd, cls = np.random.default_rng(seed), classes()
    scripts = sorted({c["script"] for c in cls})
    pools = {s: [k for k, c in enumerate(cls) if c["script"] == s] for s in scripts}
    res = {}
    for hard in (False, True):
        for n in sizes:
            right = abstain = 0
            by = {}
            for s in scripts:
                ok = 0
                for _ in range(trials):
                    imgs = np.stack([_sign(int(rnd.choice(pools[s])), rnd, hard) for _ in range(n)])
                    r = identify(probabilities(imgs))
                    ok += r["script"] == s
                    abstain += r["script"] is None
                by[s] = round(ok / trials, 2)
                right += ok
            res[f"{'unseen' if hard else 'clean'}_{n}"] = {"accuracy": round(right / (trials * len(scripts)), 3),
                                                         "abstained": round(abstain / (trials * len(scripts)), 3), "by_script": by}
    nulls = {}
    for name, make in (("blobs", _blob), ("latin_letters", _latin)):
        named = 0
        for _ in range(trials * 3):
            imgs = np.stack([make(rnd) for _ in range(6)])
            named += identify(probabilities(imgs))["script"] is not None
        nulls[name] = {"sets_of_6": trials * 3, "named_a_script": round(named / (trials * 3), 3)}
    return {"id": "script_id", "scripts": scripts, "results": res, "non_script_controls": nulls}


if __name__ == "__main__":
    r = evaluate()
    RESULT.write_text(json.dumps(r, indent=1))
    for k, v in r["results"].items():
        print(k, v["accuracy"], "abstained", v["abstained"])
    print(r["non_script_controls"])
