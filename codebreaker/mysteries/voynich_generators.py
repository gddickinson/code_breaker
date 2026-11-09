"""Which mechanism could have produced the Voynich statistics? Candidate generators, scored."""
import random
from collections import Counter

import numpy as np

from ..languages import corpus_text
from ..text import letters, strip_accents
from .voynich import glyphs, parse, profile

KEYS = ("h1", "h2", "mean_word_length", "zipf_slope", "adjacent_word_repeat_rate", "vocab_ratio")
SPREAD = {"h1": 0.15, "h2": 0.2, "mean_word_length": 0.4, "zipf_slope": 0.1, "adjacent_word_repeat_rate": 0.004, "vocab_ratio": 0.05}
VERBOSE = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "ol or ar d ch ee k sh y qo aiin dy ain o p qok r l s t y che chy aly ot kch".split()))


def latin_words(n, seed):
    w = [letters(x) for x in strip_accents(corpus_text("la")).split()]
    w = [x for x in w if x]
    st = random.Random(seed).randrange(max(1, len(w) - n))
    return (w * (n // len(w) + 1))[st: st + n]


def verbose_cipher(n, seed):
    return ["".join(VERBOSE[c] for c in w) for w in latin_words(n, seed)]


def monoalpha(n, seed):
    key = list("etaoinshrdlcumwfgypbvkjxqz")
    random.Random(seed).shuffle(key)
    return ["".join(key[ord(c) - 65] for c in w) for w in latin_words(n, seed)]


def abbreviated(n, seed):
    """Vowels removed, then each consonant given a stem and a slot-based ending."""
    return ["".join(c for c in w if c not in "AEIOU") or w[:1] for w in latin_words(n, seed)]


def self_citation(real, n, seed):
    """Timm and Schinner: copy a recent word, and sometimes alter one glyph."""
    r = random.Random(seed)
    alpha = "aoeychdlkinrst"
    out = r.sample(real, 30)
    while len(out) < n:
        w = list(out[-r.randint(1, min(len(out), 80))])
        if r.random() < 0.55:
            i = r.randrange(len(w))
            w[i] = r.choice(alpha)
        if r.random() < 0.12:
            w.insert(r.randrange(len(w) + 1), r.choice(alpha))
        if r.random() < 0.12 and len(w) > 2:
            w.pop(r.randrange(len(w)))
        out.append("".join(w))
    return out[:n]


def table_grille(real, n, seed):
    """Rugg-style: three columns of syllables sampled independently, fitted from real words."""
    r = random.Random(seed)
    split = [(w[:2], w[2:-2], w[-2:]) for w in real if len(w) >= 4]
    cols = [Counter(p[i] for p in split) for i in range(3)]
    drawn = [r.choices(list(c), weights=list(c.values()), k=n) for c in cols]
    return ["".join(x) for x in zip(*drawn)]


def char_markov(real, n, seed):
    """Baseline with the true first-order statistics: shows what H2 alone cannot explain."""
    r = random.Random(seed)
    trans = {}
    for w in real:
        for a, b in zip("^" + w, w + "$"):
            trans.setdefault(a, []).append(b)
    out = []
    for _ in range(n):
        w, c = "", "^"
        while len(w) < 14:
            c = r.choice(trans[c])
            if c == "$":
                break
            w += c
        out.append(w or "o")
    return out


def measure(words):
    words = [w for w in words if w]
    p = profile(list("".join(words)), words)
    p["vocab_ratio"] = p["vocabulary"] / p["word_count"]
    return p


def distance(a, b):
    return float(np.sqrt(np.mean([((a[k] - b[k]) / SPREAD[k]) ** 2 for k in KEYS])))


def run(n=12000) -> dict:
    real = [w for r in parse() for w in r["words"]]
    rng = random.Random(0)
    start = rng.randrange(len(real) - n)
    target = measure(real[start: start + n])
    a, b = real[: len(real) // 2], real[len(real) // 2:]
    split = distance(measure(a[:n]), measure(b[:n]))
    gens = {"Self-citation copying": lambda s: self_citation(real, n, s), "Table and grille": lambda s: table_grille(real, n, s), "Character Markov chain (fitted)": lambda s: char_markov(real, n, s),
            "Verbose cipher of Latin": lambda s: verbose_cipher(n, s), "Simple substitution of Latin": lambda s: monoalpha(n, s), "Latin with vowels removed": lambda s: abbreviated(n, s), "Plain Latin": lambda s: latin_words(n, s)}
    rows = []
    for name, g in gens.items():
        ms = [measure(g(s)) for s in range(3)]
        d = [distance(m, target) for m in ms]
        rows.append({"model": name, "distance": round(float(np.mean(d)), 2), **{k: round(float(np.mean([m[k] for m in ms])), 3) for k in KEYS}})
    rows.sort(key=lambda r: r["distance"])
    return {"id": "voynich_generators", "target": {k: round(target[k], 3) for k in KEYS}, "split_half_distance": round(split, 2), "words": n, "rows": rows}
