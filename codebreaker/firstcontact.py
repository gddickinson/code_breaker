"""First Contact lab (Round 84): is a symbol stream language-like, and is a bit stream a picture?

Profile of a stream (tokens: characters, or space-separated units): Shannon entropy of single symbols (H1), of the next
symbol given one and two before (H2, H3), the drop from H1 to H3, zlib compressibility, the share of repeated 4-grams,
and the Zipf slope of the rank-frequency curve; each sequential measure also on a shuffled copy, so structure beyond
symbol frequencies shows as a difference (sequential structure is not proof of language: birdsong has it too).
References: English and French text, synthetic birdsong (known grammar), the Voynich manuscript (EVA) and rongorongo
(recorded transcriptions in the app), and uniform random symbols.

Picture layout: a bit stream of length N is laid out at every width dividing N (and every width 2-N/2 if none fits);
each layout is scored by how often a bit equals the bit directly above it beyond what chance predicts; the best width
wins, with a z-score against the same scores for shuffled bits. The 1974 Arecibo message (1,679 bits, from the saved
Wikipedia page) is the worked example: 1,679 = 23 x 73, and its picture appears 23 wide."""
import math
import random
import re
import zlib
from collections import Counter

import numpy as np

from .languages import ROOT, corpus_text

AREC = ROOT / "data/sources/research/wp_arecibo.txt"


def arecibo_bits() -> str:
    t = AREC.read_text()
    a = t.index("{{Collapse top|Full binary message}}")
    b = t.index("{{Collapse bottom}}", a)
    return "".join(re.findall(r"[01]", re.sub(r"<[^>]+>", "", t[a:b])))


def entropy(counts: Counter) -> float:
    n = sum(counts.values())
    return -sum(c / n * math.log2(c / n) for c in counts.values()) if n else 0.0


def cond_entropy(seq: list, k: int) -> float:
    """H(next | previous k symbols)."""
    ctx = Counter(tuple(seq[i:i + k]) for i in range(len(seq) - k))
    joint = Counter(tuple(seq[i:i + k + 1]) for i in range(len(seq) - k))
    return entropy(joint) - entropy(ctx)


def zipf_slope(seq: list) -> float:
    f = np.array(sorted(Counter(seq).values(), reverse=True), float)
    if len(f) < 5:
        return float("nan")
    r = np.arange(1, len(f) + 1)
    return float(np.polyfit(np.log(r), np.log(f), 1)[0])


def _seqstats(seq: list) -> dict:
    data = "\x1f".join(map(str, seq)).encode()
    grams = Counter(tuple(seq[i:i + 4]) for i in range(len(seq) - 3))
    return {"H2": cond_entropy(seq, 1), "H3": cond_entropy(seq, 2), "compress": len(zlib.compress(data, 9)) / max(len(data), 1),
            "repeat4": sum(c for c in grams.values() if c > 1) / max(sum(grams.values()), 1)}


def profile(seq: list, seed: int = 84, max_len: int = 6000, shuffles: int = 20) -> dict:
    """Measures of the stream and, for each sequential one, z-scores against shuffled copies (same symbols, random
    order). With large alphabets H3 is underestimated from a few thousand tokens for real and shuffled streams alike,
    so the comparisons with shuffles, not the raw values, carry the evidence; H2 is the more reliable order there."""
    seq = list(seq)[:max_len]
    rnd = random.Random(seed)
    s = _seqstats(seq)
    sh = []
    for _ in range(shuffles):
        x = seq[:]
        rnd.shuffle(x)
        sh.append(_seqstats(x))
    clip = lambda v: round(max(-999.0, min(999.0, v)), 1)  # shuffled copies can have almost no spread
    z = {k: clip((float(np.mean([v[k] for v in sh])) - s[k]) / (float(np.std([v[k] for v in sh])) + 1e-9)) for k in ("H2", "H3", "compress")}
    rep = clip((s["repeat4"] - float(np.mean([v["repeat4"] for v in sh]))) / (float(np.std([v["repeat4"] for v in sh])) + 1e-9))
    h1 = entropy(Counter(seq))
    structured = z["H2"] >= 5
    return {"symbols": len(seq), "alphabet": len(set(seq)), "H1": round(h1, 3), "H2": round(s["H2"], 3), "H3": round(s["H3"], 3),
            "H2_shuffled": round(float(np.mean([v["H2"] for v in sh])), 3), "z_H2": z["H2"], "z_H3": z["H3"], "z_compress": z["compress"],
            "repeat4": round(s["repeat4"], 3), "z_repeat4": rep, "zipf_slope": round(zipf_slope(seq), 3),
            "verdict": ("sequential structure: the next symbol depends on the last (z=%.0f against shuffles); language has this, so do birdsong and machine codes" % z["H2"])
            if structured else "no sequential structure beyond symbol frequencies: consistent with random order"}


def tokens(text: str) -> list:
    """Space-separated units if the text has several, else its characters (spaces dropped)."""
    parts = text.split()
    return parts if len(parts) >= 50 and len(set(parts)) > 1 else [c for c in text if not c.isspace()]


def references() -> dict:
    from .mysteries.scriptlab import rongorongo
    from .sound.synth import song

    out = {}
    for code, name in (("en", "English letters"), ("fr", "French letters")):
        out[name] = [c for c in corpus_text(code).upper() if c.isalpha()][20000:26000]
    out["English words"] = re.findall(r"[a-z]+", corpus_text("en").lower())[5000:11000]
    out["Synthetic birdsong syllables"] = list(song(1500, seed=4)[2])
    vms = (ROOT / "data/sources/vms_ZL3b-n.txt").read_text(errors="ignore")
    eva = re.sub(r"<[^>]*>|\{[^}]*\}|#.*", " ", vms)
    out["Voynich (EVA letters)"] = [c for c in eva if c.isalpha() and c.islower()][:6000]
    out["Rongorongo signs"] = [s for w in rongorongo() for s in w][:6000]
    rnd = np.random.default_rng(84)
    out["Random letters (26)"] = list(rnd.integers(0, 26, 6000))
    return {k: profile(v) for k, v in out.items()}


def layout_score(bits: str, w: int) -> float:
    rows = len(bits) // w
    if rows < 3:
        return -1.0
    a = np.frombuffer(bits[:rows * w].encode(), np.uint8) - 48
    g = a.reshape(rows, w)
    same = float((g[1:] == g[:-1]).mean())
    p = float(a.mean())
    return same - (p * p + (1 - p) * (1 - p))


def decode_layout(bits: str, shuffles: int = 200, seed: int = 84) -> dict:
    n = len(bits)
    widths = [w for w in range(2, n // 2 + 1) if n % w == 0 and n // w >= 3] or list(range(2, max(3, n // 3)))
    scores = {w: layout_score(bits, w) for w in widths}
    best = max(scores, key=scores.get)
    rnd = random.Random(seed)
    null = []
    for _ in range(shuffles):
        b = list(bits)
        rnd.shuffle(b)
        sb = "".join(b)
        null.append(max(layout_score(sb, w) for w in widths))
    mu, sd = float(np.mean(null)), float(np.std(null)) + 1e-9
    return {"length": n, "factors": [w for w in range(2, n) if n % w == 0], "widths_tried": len(widths), "best_width": best,
            "rows": n // best, "score": round(scores[best], 4), "z": round((scores[best] - mu) / sd, 1),
            "ranking": sorted(({"width": w, "score": round(s, 4)} for w, s in scores.items()), key=lambda x: -x["score"])[:6],
            "grid": [bits[i * best:(i + 1) * best] for i in range(n // best)]}


def picture(w: int, h: int, rnd: np.random.Generator) -> str:
    """A random picture of filled rectangles and lines, w x h, as a bit string (a stand-in for a designed message)."""
    import cv2

    g = np.zeros((h, w), np.uint8)
    for _ in range(int(rnd.integers(3, 7))):
        x0, y0 = int(rnd.integers(0, w - 2)), int(rnd.integers(0, h - 2))
        x1, y1 = int(rnd.integers(x0 + 1, w)), int(rnd.integers(y0 + 1, h))
        if rnd.random() < 0.5:
            cv2.rectangle(g, (x0, y0), (x1, y1), 1, -1)
        else:
            cv2.line(g, (x0, y0), (x1, y1), 1, 1)
    return "".join(map(str, g.ravel()))


def layout_controls(sizes=((17, 29), (19, 31), (23, 47), (13, 61)), trials: int = 10, seed: int = 84) -> dict:
    """Pictures of prime-by-prime sizes: is the width recovered? Random bits of the same lengths: how high is z?"""
    rnd = np.random.default_rng(seed)
    pics, rand_z = {}, []
    for w, h in sizes:
        ok = 0
        for _ in range(trials):
            ok += decode_layout(picture(w, h, rnd), shuffles=60)["best_width"] == w
        pics[f"{w}x{h}"] = round(ok / trials, 2)
        for _ in range(trials // 2):
            rand_z.append(decode_layout("".join(map(str, rnd.integers(0, 2, w * h))), shuffles=60)["z"])
    return {"pictures_width_recovered": pics, "random_bits_z_max": max(rand_z), "random_bits_z_mean": round(float(np.mean(rand_z)), 2)}


RESULT = ROOT / "data/results/firstcontact.json"
PICTURE_Z = 4.0  # random bits stayed under z=2.1 in the controls


def run() -> dict:
    arec = decode_layout(arecibo_bits())
    return {"id": "firstcontact", "references": references(), "arecibo": {k: arec[k] for k in ("length", "factors", "best_width", "rows", "z", "ranking")},
            "layout_controls": layout_controls()}


if __name__ == "__main__":
    import json

    r = run()
    RESULT.write_text(json.dumps(r, indent=1))
    print(json.dumps({"arecibo": r["arecibo"], "layout_controls": r["layout_controls"]}, indent=1))
