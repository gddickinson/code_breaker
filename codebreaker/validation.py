"""False-positive controls: no mystery result counts unless it survives these."""
import random

import numpy as np

from .attacks.classical import solve_symbols
from .languages import corpus_text, score
from .text import letters, similarity


def sample_plaintext(n: int, lang: str = "en", seed: int = 0) -> str:
    text = letters(corpus_text(lang))
    r = random.Random(seed)
    start = r.randrange(5000, len(text) - n - 5000)
    return text[start:start + n]


def homophonic_like(symbols: list, plain: str, seed: int = 0) -> list:
    """Encrypt plain so the result has the same number of distinct symbols as the target."""
    r = random.Random(seed)
    k = len(set(symbols))
    letters_used = sorted(set(plain))
    weights = np.array([plain.count(c) for c in letters_used], dtype=float)
    alloc = np.maximum(1, np.floor(weights / weights.sum() * k)).astype(int)
    pool = list(range(k))
    r.shuffle(pool)
    table, p = {}, 0
    for c, a in zip(letters_used, alloc):
        table[c] = pool[p:p + a] or [pool[0]]
        p += a
    return [r.choice(table[c]) for c in plain]


def null_test(symbols, lang="en", homophonic=False, n_null=12, seed=0, iters=None, restarts=4) -> dict:
    """Compare the solver's score on the real order against scrambled copies of the same symbols."""
    real = solve_symbols(list(symbols), lang, homophonic, iters, restarts, seed)
    r = random.Random(seed + 1)
    nulls = []
    for i in range(n_null):
        s = list(symbols)
        r.shuffle(s)
        nulls.append(solve_symbols(s, lang, homophonic, iters, restarts, seed + 2 + i)["score"])
    mean, sd = float(np.mean(nulls)), float(np.std(nulls, ddof=1)) if n_null > 1 else 0.0
    z = (real["score"] - mean) / sd if sd > 0 else 0.0
    return {"plaintext": real["plaintext"], "score": real["score"], "null_mean": round(mean, 3), "null_sd": round(sd, 3),
            "z": round(z, 2), "p_empirical": round((1 + sum(n >= real["score"] for n in nulls)) / (n_null + 1), 3), "lang": lang}


def positive_control(symbols, lang="en", homophonic=False, seed=0, iters=None, restarts=4, trials=3) -> dict:
    """Could this solver recover a message of this exact size and symbol count?"""
    acc = []
    for t in range(trials):
        plain = sample_plaintext(len(symbols), lang, seed + t)
        if homophonic:
            enc = homophonic_like(list(symbols), plain, seed + t)
        else:
            alpha = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            random.Random(seed + t).shuffle(alpha)
            enc = [alpha[ord(c) - 65] for c in plain]
        got = solve_symbols(enc, lang, homophonic, iters, restarts, seed + t + 50)["plaintext"]
        acc.append(similarity(plain, got))
    return {"accuracies": [round(a, 3) for a in acc], "mean": round(float(np.mean(acc)), 3)}


def verdict(pos_mean: float, z: float, tests: int = 1) -> str:
    """Plain-language outcome, with the z threshold raised for the number of hypotheses tried."""
    bar = 4.0 + np.log10(max(tests, 1))
    if pos_mean < 0.7:
        return f"Inconclusive: this solver recovers only {pos_mean:.0%} of a known message of this size, so a failure here says little."
    if z >= bar:
        return f"Candidate signal (z={z:.1f} over a bar of {bar:.1f}). Needs independent human reading before any claim."
    return f"No evidence: the solver can read a text of this size ({pos_mean:.0%}), but the real ciphertext scores like scrambled symbols (z={z:.1f})."
