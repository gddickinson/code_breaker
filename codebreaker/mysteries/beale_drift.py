"""Could an honest encoder working through one region of a text produce Beale's correlations?"""
import random
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from ..text import to_ints
from ..validation import sample_plaintext
from .beale import ciphers, initials


def encode(plain, doc, window, drift, seed):
    """Keep a current page; pick matching words near it, moving the page with probability drift."""
    r = random.Random(seed)
    n = len(doc)
    centre = r.randrange(n)
    out = []
    for c in plain:
        if r.random() < drift:
            centre = r.randrange(n)
        lo, hi = max(0, centre - window), min(n, centre + window)
        hits = [i for i in range(lo, hi) if doc[i] == c]
        while not hits and (lo > 0 or hi < n):
            lo, hi = max(0, lo - window), min(n, hi + window)
            hits = [i for i in range(lo, hi) if doc[i] == c]
        out.append((r.choice(hits) if hits else centre) + 1)
    return out


def measure(nums):
    a = np.array(nums, dtype=float)
    return {"lag1": float(np.corrcoef(a[:-1], a[1:])[0, 1]), "distinct": len(set(nums)) / len(nums)}


def job(a):
    window, drift, n, size = a
    doc = to_ints(initials("key_kjv.txt")[20000: 20000 + size])
    ms = [measure(encode(to_ints(sample_plaintext(n, "en", s)), doc, window, drift, s)) for s in range(25)]
    return {"window": window, "drift": drift, "lag1": round(float(np.mean([m["lag1"] for m in ms])), 3), "lag1_sd": round(float(np.std([m["lag1"] for m in ms])), 3), "distinct": round(float(np.mean([m["distinct"] for m in ms])), 3)}


def run() -> dict:
    c = ciphers()
    targets = {k: {kk: round(v, 3) for kk, v in measure(c[k]).items()} for k in c}
    size = 1000
    jobs = [(w, d, 618, size) for w in (10, 25, 50, 100, 200, 400) for d in (0.01, 0.03, 0.1, 0.3, 1.0)]
    with ProcessPoolExecutor(4) as ex:
        rows = list(ex.map(job, jobs))
    def near(t):
        return sorted(rows, key=lambda r: abs(r["lag1"] - t["lag1"]) / 0.05 + abs(r["distinct"] - t["distinct"]) / 0.05)[:3]
    return {"id": "beale_drift", "targets": targets, "doc_size": size, "grid": rows, "closest_B1": near(targets["B1"]), "closest_B3": near(targets["B3"]), "closest_B2": near(targets["B2"])}
