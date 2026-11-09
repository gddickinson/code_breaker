"""Liber Primus: page-level attacks in the Gematria Primus alphabet, with solved pages as controls."""
import random
import re

import numpy as np

from ..languages import ROOT, corpus_text, score
from ..segment import segment
from ..text import letters
from ..validation import coverage

FILE = ROOT / "data/sources/scripts_lab/liberprimus.txt"
RUNES = "ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛂᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
NAMES = "F U TH O R C G W H N I J EO P X S T B E M L NG OE D A AE Y IA EA".split()
N = 29
PRIMES = [p for p in range(2, 20000) if all(p % q for q in range(2, int(p ** 0.5) + 1))]


def pages():
    raw = FILE.read_text(errors="ignore")
    out = {}
    for no, body in re.findall(r"-+ (\d+) -+\n(.*?)(?=-+ \d+ -+|\Z)", raw, flags=re.S):
        seq = [RUNES.index(c) for c in body if c in RUNES]
        if len(seq) >= 30:
            out[int(no)] = seq
    return out


def to_latin(seq):
    return "".join(NAMES[i] for i in seq)


def english_runes():
    t = letters(corpus_text("en"))[:400000].replace("TH", "1").replace("NG", "2").replace("EO", "3").replace("OE", "4").replace("AE", "5").replace("IA", "6").replace("EA", "7").replace("K", "C").replace("Q", "C").replace("V", "U").replace("Z", "S")
    m = {"1": "TH", "2": "NG", "3": "EO", "4": "OE", "5": "AE", "6": "IA", "7": "EA"}
    return np.bincount([NAMES.index(m.get(c, c)) for c in t], minlength=N) / len(t)


LOG = np.log(english_runes() + 1e-6)


def ic(seq):
    c = np.bincount(seq, minlength=N)
    n = len(seq)
    return float((c * (c - 1)).sum() / (n * (n - 1)))


def attacks(seq):
    """Candidate decryptions as (name, runes). Solved pages used shifts, Vigenere and prime streams."""
    a = np.array(seq)
    n = len(a)
    for s in range(N):
        yield f"shift {s}", (a + s) % N
        yield f"atbash then shift {s}", (N - 1 - a + s) % N
    idx = np.arange(n)
    phi = np.array([p - 1 for p in PRIMES[:n]])
    prime = np.array(PRIMES[:n])
    for label, st in (("prime stream", prime), ("totient stream", phi), ("position", idx)):
        for sign in (1, -1):
            for s in (0, 1, -1):
                yield f"{label} sign {sign} offset {s}", (a + sign * (st + s)) % N
    for period in range(2, 21):
        key = np.zeros(period, dtype=int)
        for c in range(period):
            key[c] = int(np.argmax([LOG[(a[c::period] - k) % N].sum() for k in range(N)]))
        yield f"period {period} key", (a - np.resize(key, n)) % N


def best(seq):
    top = (-99.0, "", None)
    for name, plain in attacks(seq):
        s = score(to_latin(plain.tolist()))
        if s > top[0]:
            top = (s, name, plain)
    return top


def run(n_null=12) -> dict:
    rows, r = [], random.Random(0)
    for no, seq in sorted(pages().items()):
        s, name, plain = best(seq)
        shuf = list(seq)
        nulls = []
        for _ in range(n_null):
            r.shuffle(shuf)
            nulls.append(best(shuf)[0])
        m, sd = float(np.mean(nulls)), float(np.std(nulls, ddof=1))
        z = round((s - m) / sd, 2) if sd else 0.0
        text = to_latin(plain.tolist())
        rows.append({"page": no, "runes": len(seq), "ic": round(ic(seq), 4), "attack": name, "score": round(s, 3), "null_mean": round(m, 3), "z": z, "coverage": coverage(text[:600]), "reading": segment(text[:160])})
    return {"id": "liber_primus", "uniform_ic": round(1 / N, 4), "english_rune_ic": round(float((english_runes() ** 2).sum()), 4), "rows": rows}
