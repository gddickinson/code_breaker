"""Could the Tamam Shud code be the initials of a memorised text? Fuzzy search across large books."""
import random
import re
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from numba import njit

from ..languages import ROOT, corpus_text
from ..text import to_ints
from .tamam import CODE, LINES

SRC = ROOT / "data/sources"
TEXTS = {"King James Bible": "key_kjv.txt", "Shakespeare": "key_shakespeare.txt", "Rubaiyat": "key_rubaiyat.txt", "Federalist Papers": "key_federalist.txt", "Common Sense": "key_common_sense.txt", "US Constitution": "key_constitution.txt"}


@njit(cache=True)
def min_hamming(p, t):
    best, at = len(p), -1
    for i in range(len(t) - len(p) + 1):
        d = 0
        for j in range(len(p)):
            d += p[j] != t[i + j]
            if d >= best:
                break
        if d < best:
            best, at = d, i
    return best, at


def initials(name):
    raw = (SRC / name).read_text(errors="ignore")
    s, e = re.search(r"\*\*\* START OF.*?\*\*\*", raw), raw.find("*** END OF")
    return to_ints("".join(w[0].upper() for w in re.findall(r"[A-Za-z]+", raw[s.end() if s else 0: e if e > 0 else None])))


def total(blocks, t):
    return int(sum(min_hamming(b, t)[0] for b in blocks))


def job(a):
    label, n_null, seed = a
    t = initials(TEXTS[label])
    blocks = [to_ints(line) for line in LINES]
    real = total(blocks, t)
    full, at = min_hamming(to_ints(CODE), t)
    r = random.Random(seed)
    src = to_ints("".join(w[0].upper() for w in re.findall(r"[A-Za-z]+", corpus_text("en"))))
    nulls, fnull = [], []
    for _ in range(n_null):
        bl = [src[(st := r.randrange(len(src) - 20)): st + len(x)] for x in LINES]
        nulls.append(total(bl, t))
        st = r.randrange(len(src) - 50)
        fnull.append(min_hamming(src[st: st + len(CODE)], t)[0])
    return {"text": label, "initials": len(t), "line_mismatches": real, "null_mean": round(float(np.mean(nulls)), 2), "p_lines": round((1 + sum(n <= real for n in nulls)) / (n_null + 1), 4), "whole_code_mismatches": int(full), "whole_null_mean": round(float(np.mean(fnull)), 2), "p_whole": round((1 + sum(n <= full for n in fnull)) / (n_null + 1), 4)}


def control(seed=2):
    """A hidden 44-letter passage of the Bible, with 4 misread letters, must be found."""
    t = initials(TEXTS["King James Bible"])
    r = random.Random(seed)
    st = r.randrange(100000, len(t) - 100)
    p = t[st: st + 44].copy()
    for i in r.sample(range(44), 4):
        p[i] = (p[i] + 7) % 26
    d, at = min_hamming(p, t)
    return {"planted": st, "found": int(at), "mismatches": int(d), "success": int(at) == st}


def run() -> dict:
    with ProcessPoolExecutor(3) as ex:
        rows = list(ex.map(job, [(k, 150, i) for i, k in enumerate(TEXTS)]))
    return {"id": "tamam_mnemonic", "control": control(), "rows": sorted(rows, key=lambda r: r["p_lines"]), "tests": 2 * len(rows)}
