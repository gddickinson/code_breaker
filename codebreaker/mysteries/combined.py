"""Combined transposition and homophonic substitution, and a true two-letter (bigram) solver."""
import math
import random
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from numba import njit

from ..attacks.classical import solve_symbols, symbols_to_ints
from ..kernels import quad_score
from ..languages import ROOT, model
from ..segment import segment
from ..text import A, letters, similarity, to_text
from ..validation import coverage, homophonic_like, sample_plaintext
from .sweep import tokens

DIR = ROOT / "data/sources/benchmark"


def repeats_at(t, p):
    pairs = [(t[i], t[i + p]) for i in range(len(t) - p)]
    return len(pairs) - len(set(pairs))


def best_periods(t, top=4, max_p=None):
    """Distances with unusually many repeated pairs, as z-scores against shuffled symbols."""
    n, r = len(t), random.Random(3)
    max_p = max_p or min(n // 2, 120)
    real = {p: repeats_at(t, p) for p in range(1, max_p + 1)}
    s = list(t)
    nulls = []
    for _ in range(12):
        r.shuffle(s)
        nulls += [repeats_at(s, p) for p in range(2, min(max_p, 60))]
    m, sd = float(np.mean(nulls)), float(np.std(nulls)) + 1e-9
    return sorted(((round((v - m) / sd, 2), p) for p, v in real.items() if p > 1), reverse=True)[:top]


def period_read(t, p):
    n = len(t)
    return [t[(i * p) % n] for i in range(n)] if math.gcd(p, n) == 1 else None


def columns_read(t, p):
    n = len(t)
    h = n // p
    out = [None] * n
    pos = 0
    for c in range(p):
        count = h + (c < n % p)
        out[c::p] = t[pos:pos + count]
        pos += count
    return out


def inverse_period(t, p):
    n = len(t)
    if math.gcd(p, n) != 1:
        return None
    out = [None] * n
    for i in range(n):
        out[(i * p) % n] = t[i]
    return out


def candidates(t):
    yield "as written", list(t)
    for z, p in best_periods(t):
        for name, fn in (("step", period_read), ("inverse step", inverse_period), ("columns", columns_read)):
            r = fn(list(t), p)
            if r:
                yield f"{name} {p} (z={z})", r


def judge(seq, seed=1):
    r = solve_symbols(seq, "en", len(set(seq)) > 26, restarts=4, seed=seed)
    return coverage(letters(r["plaintext"])[:500], "en"), r


def attack(t, seed=1):
    best = None
    for name, seq in candidates(t):
        c, r = judge(seq, seed)
        if best is None or c > best["coverage"]:
            best = {"coverage": c, "method": name, "plaintext": r["plaintext"], "score": r["score"]}
    return best


@njit(cache=True)
def _fit(p, table, letter, w):
    c = np.bincount(p, minlength=26)
    n = len(p)
    return quad_score(p, table) - w * float((((c - n * letter) ** 2) / (n * letter + 1e-9)).sum())


@njit(cache=True)
def anneal_bigram(ct, n_sym, table, iters, restarts, seed, t0, letter, w):
    """Each cipher pair maps to a plaintext pair: key[a] = 26*x + y."""
    np.random.seed(seed)
    n = len(ct)
    plain = np.zeros(2 * n, dtype=np.int32)
    best = -1e18
    best_key = np.zeros(n_sym, dtype=np.int32)
    for _ in range(restarts):
        key = np.random.randint(0, 676, n_sym).astype(np.int32)
        for i in range(n):
            plain[2 * i] = key[ct[i]] // 26
            plain[2 * i + 1] = key[ct[i]] % 26
        cur = _fit(plain, table, letter, w)
        for it in range(iters):
            temp = t0 * (1 - it / iters) + 1e-3
            a = np.random.randint(n_sym)
            old = key[a]
            if np.random.random() < 0.5:
                key[a] = (old // 26) * 26 + np.random.randint(26)
            else:
                key[a] = np.random.randint(26) * 26 + old % 26
            for i in range(n):
                if ct[i] == a:
                    plain[2 * i] = key[a] // 26
                    plain[2 * i + 1] = key[a] % 26
            s = _fit(plain, table, letter, w)
            if s >= cur or np.random.random() < np.exp((s - cur) / temp):
                cur = s
                if cur > best:
                    best, best_key = cur, key.copy()
            else:
                key[a] = old
                for i in range(n):
                    if ct[i] == a:
                        plain[2 * i] = old // 26
                        plain[2 * i + 1] = old % 26
    return best_key, best


def bigram_solve(text, seed=1, iters=2500000, restarts=4, w=2.0, tf=2.0):
    pairs = [text[i:i + 2] for i in range(0, len(text) - 1, 2)]
    c, alpha = symbols_to_ints(pairs)
    k, s = anneal_bigram(c, len(alpha), model("en")["table"], iters, restarts, seed, tf * (len(pairs) / 400) ** 0.5, model("en")["letter"], w)
    plain = "".join(A[int(k[x]) // 26] + A[int(k[x]) % 26] for x in c)
    return plain, s


def planted_combined(n, symbols, p, seed):
    plain = sample_plaintext(n, "en", seed)
    enc = homophonic_like(list(range(symbols)), plain, seed)
    out = [None] * n
    for i in range(n):
        out[(i * p) % n] = enc[i]
    return plain, out


def control_job(a):
    seed, n, sym, p = a
    plain, enc = planted_combined(n, sym, p, seed)
    z = best_periods(enc, 6)
    found = any(q == p or (q * p) % n in (1, n - 1) for _, q in z)
    r = attack(enc, seed)
    return {"period_found": found, "coverage": r["coverage"], "accuracy": round(similarity(plain, r["plaintext"]), 3), "method": r["method"]}


def bigram_control(seed=2):
    plain = sample_plaintext(1000, "en", seed)
    plain = plain[: len(plain) // 2 * 2]
    r = random.Random(seed)
    pairs = sorted({plain[i:i + 2] for i in range(0, len(plain) - 1, 2)})
    cipher = r.sample([a + b for a in A for b in A], len(pairs))
    table = dict(zip(pairs, cipher))
    ct = "".join(table[plain[i:i + 2]] for i in range(0, len(plain) - 1, 2))
    got, _ = bigram_solve(ct, seed)
    return round(similarity(plain, got), 3)


def bench_job(path):
    t = tokens(path.read_text(errors="ignore"))
    if len(t) < 60:
        return None
    r = attack(t)
    return {"name": path.stem, "length": len(t), "symbols": len(set(t)), "coverage": r["coverage"], "method": r["method"], "reading": segment(letters(r["plaintext"])[:130]), "readable": r["coverage"] >= 0.55}


def bigram_job(path):
    t = letters(path.read_text(errors="ignore"))
    if len(t) < 100:
        return None
    best = None
    for shift in (0, 1):
        p, s = bigram_solve(t[shift:])
        c = coverage(p[:500], "en")
        if best is None or c > best[0]:
            best = (c, p, shift)
    return {"name": path.stem, "length": len(t), "coverage": best[0], "shift": best[2], "reading": segment(best[1][:130]), "readable": best[0] >= 0.55}


def run() -> dict:
    with ProcessPoolExecutor(6) as ex:
        ctrl = list(ex.map(control_job, [(s, 340, 63, p) for s, p in enumerate([19, 7, 23, 37, 11, 29])]))
        combined = [r for r in ex.map(bench_job, sorted((DIR / "Substitution_and_transposition").glob("*.txt")), chunksize=2) if r]
        bigrams = [r for r in ex.map(bigram_job, sorted((DIR / "Bigram_substitution").glob("*.txt"))) if r]
    return {"id": "combined", "control": ctrl, "bigram_control": bigram_control(), "combined_rows": sorted(combined, key=lambda r: -r["coverage"]), "combined_readable": sum(r["readable"] for r in combined), "combined_total": len(combined), "bigram_rows": sorted(bigrams, key=lambda r: -r["coverage"]), "bigram_readable": sum(r["readable"] for r in bigrams)}
