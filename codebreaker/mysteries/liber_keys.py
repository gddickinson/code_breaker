"""Liber Primus: running keys from its own solved text and from known community keywords."""
import random

import numpy as np

from ..languages import score
from ..segment import segment
from ..validation import coverage
from .liber_primus import N, NAMES, pages, to_latin

KEYWORDS = ["DIVINITY", "CIRCUMFERENCE", "FIRFUMFERENCE", "KOAN", "PARABLE", "INSTAR", "EMERGENCE", "WISDOM", "PRIMES", "TOTIENT", "CICADA", "THREETHREEZEROONE", "LIBERPRIMUS"]


def runes_of(word):
    out, i = [], 0
    two = {"TH", "EO", "NG", "OE", "AE", "IA", "EA"}
    table = {**{n: k for k, n in enumerate(NAMES)}, "K": 5, "Q": 5, "V": 1, "Z": 15}
    while i < len(word):
        if word[i:i + 2] in two:
            out.append(table[word[i:i + 2]])
            i += 2
        else:
            out.append(table[word[i]])
            i += 1
    return out


def attempts(seq, keys):
    a = np.array(seq)
    for name, key in keys:
        k = np.array(key)
        n = len(a)
        if len(k) >= n:
            windows = range(0, min(len(k) - n + 1, 2500))
            for off in windows:
                part = k[off:off + n]
                for sign, op in (("minus", (a - part) % N), ("plus", (a + part) % N)):
                    yield f"{name} {sign} offset {off}", op
        else:
            r = np.resize(k, n)
            for sign, op in (("minus", (a - r) % N), ("plus", (a + r) % N)):
                yield f"{name} {sign}", op


def best(seq, keys):
    top = (-99.0, "", None)
    for name, p in attempts(seq, keys):
        s = score(to_latin(p.tolist()))
        if s > top[0]:
            top = (s, name, p)
    return top


def control(p, keys, seed=1):
    """Encrypt the plain page 57 under another page as a running key; it must be recovered."""
    plain = p[57]
    key_name, key_seq = keys[0]
    r = random.Random(seed)
    off = r.randrange(0, max(1, len(key_seq) - len(plain)))
    ct = ((np.array(plain) + np.array(key_seq[off:off + len(plain)])) % N).tolist()
    s, name, got = best(ct, keys[:1])
    return {"planted_offset": off, "found": name, "recovered": got.tolist() == plain}


def run(n_null=6) -> dict:
    p = pages()
    corpus = p[57] + p[56]
    long_keys = [("pages 56 and 57", corpus), ("reversed pages 56 and 57", corpus[::-1])]
    for no, seq in sorted(p.items()):
        if no not in (56, 57) and len(seq) > 200:
            long_keys.append((f"page {no}", seq))
    words = [(w, runes_of(w)) for w in KEYWORDS]
    keys = words + long_keys[:2]
    r, rows = random.Random(0), []
    for no, seq in sorted(p.items()):
        if no in (56, 57):
            continue
        s, name, pl = best(seq, keys)
        sh, nulls = list(seq), []
        for _ in range(n_null):
            r.shuffle(sh)
            nulls.append(best(sh, keys)[0])
        z = round((s - float(np.mean(nulls))) / (float(np.std(nulls, ddof=1)) + 1e-9), 2)
        text = to_latin(pl.tolist())
        rows.append({"page": no, "key": name, "score": round(s, 3), "z": z, "coverage": coverage(text[:600]), "reading": segment(text[:120])})
    rows.sort(key=lambda x: -x["z"])
    return {"id": "liber_keys", "control": control(p, [("page 0", p[min(p)])]), "keywords": KEYWORDS, "pages": len(rows), "rows": rows[:15], "max_coverage": max(x["coverage"] for x in rows)}
