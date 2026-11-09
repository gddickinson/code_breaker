"""False-positive controls: no mystery result counts unless it survives these."""
import random
from functools import lru_cache

import numpy as np

from .attacks.classical import solve_symbols
from .languages import corpus_text, model
from .segment import segment
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


def coverage(text: str, lang: str = "en") -> float:
    """Fraction of letters inside dictionary words of 4+ letters after segmentation."""
    words = _vocab(lang)
    parts = segment(text, lang).split()
    return round(sum(len(w) for w in parts if len(w) >= 4 and w in words) / max(sum(map(len, parts)), 1), 3)


@lru_cache(maxsize=None)
def _vocab(lang: str) -> frozenset:
    return frozenset(str(w) for w in model(lang)["words"][:20000])


def positive_control(symbols, lang="en", homophonic=False, seed=0, iters=None, restarts=4, trials=3) -> dict:
    """Could this solver recover a message of this size? Also records what a real solve looks like."""
    acc, scores, cov = [], [], []
    for t in range(trials):
        plain = sample_plaintext(len(symbols), lang, seed + t)
        if homophonic:
            enc = homophonic_like(list(symbols), plain, seed + t)
        else:
            alpha = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            random.Random(seed + t).shuffle(alpha)
            enc = [alpha[ord(c) - 65] for c in plain]
        got = solve_symbols(enc, lang, homophonic, iters, restarts, seed + t + 50)
        acc.append(similarity(plain, got["plaintext"]))
        scores.append(got["score"])
        cov.append(coverage(plain, lang))
    return {"accuracies": [round(a, 3) for a in acc], "mean": round(float(np.mean(acc)), 3), "solved_score": round(float(np.mean(scores)), 3), "true_coverage": round(float(np.mean(cov)), 3)}


READABLE = "Readable candidate"


def verdict(pc: dict, z: float, tests: int = 1, plaintext: str = "", score: float | None = None, lang: str = "en") -> str:
    """Three gates: the solver works at this size, it beats shuffles, and the output reads like text.

    Beating a shuffled copy only proves sequential structure. Many unsolved texts have that
    without any solution existing, so a result must also match a genuine solve of this size.
    """
    bar = 4.0 + float(np.log10(max(tests, 1)))
    if pc["mean"] < 0.7:
        return f"Inconclusive: this solver recovers only {pc['mean']:.0%} of a known message of this size, so a failure here says little."
    if z < bar:
        return f"No evidence: the solver can read a text of this size ({pc['mean']:.0%}), but the real ciphertext scores like scrambled symbols (z={z:.1f})."
    cov = coverage(plaintext, lang) if plaintext else 0.0
    if score is not None and score >= pc["solved_score"] - 0.2 and cov >= 0.8 * pc["true_coverage"]:
        return f"{READABLE} (z={z:.1f}, word coverage {cov:.0%}). Needs independent human reading before any claim."
    got = "n/a" if score is None else f"{score:.2f}"
    return f"Structure only: the symbol order is non-random (z={z:.1f}), but the output does not read as text (score {got} against {pc['solved_score']:.2f} for a real solve; word coverage {cov:.0%} against {pc['true_coverage']:.0%})."
