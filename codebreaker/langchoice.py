"""Which languages to try on a ciphertext (Round 85b), chosen from letter statistics before any attack.

With 18 cipher languages the crack cannot try them all, so it keeps the k that fit best. The fit depends on what the
cipher has done to the letters, so the choice is staged:
1. letters left as they are (plain text, transposition): distance between the text's letter frequencies and each
   language's (KL divergence), used when the best language fits within PLAIN_FIT;
2. a periodic polyalphabetic cipher (index of coincidence low, a period whose columns have a language-like IC): each
   column is a Caesar shift of the language, so each column is fitted at its best shift;
3. otherwise (simple substitution): a key is annealed quickly in each language and the solved text's quadgram score
   is compared with real text of that language and length (z); sorted letter frequencies alone were too weak (top-3
   hit rate 0.54 at 150 letters, 0.87 at 400; solving lifts it to 0.97 at both, in under a second).
Evaluated on corpus passages under each cipher (scripts in the session log; results in tests/test_langchoice.py)."""
from functools import lru_cache

import numpy as np

from .kernels import anneal_mapping, quad_score
from .languages import cipher_langs, corpus_text, model
from .text import letters, to_ints

PLAIN_FIT = 0.25   # KL (nats) of the best language for letters that are unchanged; substituted text sits far above
POLY_IC = 0.052    # below this the letters are flattened: try periods


def _freq(a: np.ndarray) -> np.ndarray:
    return np.bincount(a, minlength=26) / max(len(a), 1)


def _kl(p: np.ndarray, q: np.ndarray) -> float:
    q = np.clip(q, 1e-6, 1)
    m = p > 0
    return float(np.sum(p[m] * np.log(p[m] / q[m])))


def ic(a: np.ndarray) -> float:
    c = np.bincount(a, minlength=26)
    n = c.sum()
    return float((c * (c - 1)).sum() / (n * (n - 1))) if n > 1 else 0.0


def period(a: np.ndarray, max_p: int = 20) -> int:
    """The smallest period whose columns' mean IC comes within 90% of the best (multiples of the true period score
    as well as it does)."""
    scores = {p: np.mean([ic(a[i::p]) for i in range(p)]) for p in range(1, min(max_p, len(a) // 8) + 1)}
    best = max(scores.values())
    return min(p for p, s in scores.items() if s >= 0.9 * best)


def lang_ic(code: str) -> float:
    q = model(code)["letter"]
    return float((q * q).sum())


def distances(raw: str) -> tuple[str, dict]:
    """(the stage used, {language: distance}); smaller is closer."""
    a = np.frombuffer(letters(raw).encode(), np.uint8).astype(np.int64) - 65
    obs = _freq(a)
    langs = cipher_langs()
    plain = {c: _kl(obs, model(c)["letter"]) for c in langs}
    if min(plain.values()) <= PLAIN_FIT:
        return "letters unchanged", plain
    if ic(a) < POLY_IC and len(a) >= 60:
        p = period(a)
        if p > 1:
            cols = [_freq(a[i::p]) for i in range(p)]
            out = {}
            for c in langs:
                q = model(c)["letter"]
                out[c] = float(np.mean([min(_kl(col, np.roll(q, s)) for s in range(26)) for col in cols]))
            return f"polyalphabetic, period {p}", out
    quick = {c: -_solved_z(a[:SOLVE_LEN], c) for c in langs}
    for c in sorted(quick, key=quick.get)[:6]:  # a quick anneal can miss; the six best get a thorough one
        quick[c] = min(quick[c], -_solved_z(a[:SOLVE_LEN], c, 40000, 4))
    return "substitution", quick


SOLVE_LEN = 250


@lru_cache(maxsize=None)
def _baseline(code: str, n: int = SOLVE_LEN) -> tuple[float, float]:
    """Mean and spread of the quadgram score of real text windows of n letters in the language."""
    t = to_ints(corpus_text(code))
    rnd = np.random.default_rng(85)
    s = [quad_score(t[i:i + n], model(code)["table"]) / (n - 3) for i in rnd.integers(0, len(t) - n, 40)]
    return float(np.mean(s)), float(np.std(s)) + 1e-6


def _solved_z(a: np.ndarray, code: str, iters: int = 20000, restarts: int = 3) -> float:
    """A simple substitution solved quickly in the language; how close its score comes to the language's own text
    (z against real windows: near 0 = as good as real text, far below = the language does not fit)."""
    m = model(code)
    ct = a.astype(np.int32)
    key, _ = anneal_mapping(ct, 26, m["table"], iters, restarts, 85, False, 3.0, m["letter"], 0.0)
    plain = key[ct].astype(np.int32)
    mu, sd = _baseline(code, len(ct))
    return (quad_score(plain, m["table"]) / (len(ct) - 3) - mu) / sd


def choose(raw: str, k: int = 3) -> list[str]:
    if len(letters(raw)) < 20:
        return ["en", "fr", "de"][:k]
    _, d = distances(raw)
    return sorted(d, key=d.get)[:k]
