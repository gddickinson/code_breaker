"""Homophonic annealing over a 5-gram table, for when quadgrams overfit dense ciphers."""
import numpy as np
from numba import njit

from .languages import MODELS, ROOT, corpus_text
from .text import letters, to_ints

PATH = MODELS / "en_5gram.npy"
EXTRA = ("key_federalist.txt", "key_common_sense.txt", "declaration.txt")


def table5() -> np.ndarray:
    if PATH.exists():
        return np.load(PATH, mmap_mode="r")
    parts = [corpus_text("en")] + [(ROOT / "data/sources" / f).read_text(errors="ignore") for f in EXTRA]
    t = to_ints(" ".join(parts)).astype(np.int64)
    idx = t[:-4] * 456976 + t[1:-3] * 17576 + t[2:-2] * 676 + t[3:-1] * 26 + t[4:]
    c = np.bincount(idx, minlength=26 ** 5).astype(np.float64)
    tab = np.log10((c + 0.02) / (c.sum() + 0.02 * 26 ** 5)).astype(np.float32)
    PATH.parent.mkdir(parents=True, exist_ok=True)
    np.save(PATH, tab)
    return tab


@njit(cache=True)
def score5(p, table):
    s = 0.0
    for i in range(len(p) - 4):
        s += table[p[i] * 456976 + p[i + 1] * 17576 + p[i + 2] * 676 + p[i + 3] * 26 + p[i + 4]]
    return s


@njit(cache=True)
def anneal5(ct, n_sym, table, letter, w, iters, restarts, seed, t0):
    np.random.seed(seed)
    n = len(ct)
    counts = np.bincount(ct, minlength=n_sym)
    start = np.zeros(n_sym + 1, dtype=np.int64)
    for i in range(n_sym):
        start[i + 1] = start[i] + counts[i]
    pos = np.zeros(n, dtype=np.int64)
    fill = start[:-1].copy()
    for i in range(n):
        pos[fill[ct[i]]] = i
        fill[ct[i]] += 1
    stamp = np.zeros(n, dtype=np.int64)
    windows = np.zeros(n * 5 + 5, dtype=np.int64)
    expected = n * letter + 1e-9
    best, best_key, tick = -1e18, np.zeros(n_sym, dtype=np.int32), 0
    plain = np.zeros(n, dtype=np.int64)
    for _ in range(restarts):
        key = np.minimum(np.searchsorted(np.cumsum(letter), np.random.random(n_sym)), 25).astype(np.int32)
        for i in range(n):
            plain[i] = key[ct[i]]
        lc = np.bincount(plain, minlength=26).astype(np.float64)
        cur = score5(plain, table) - w * float((((lc - expected) ** 2) / expected).sum())
        for it in range(iters):
            temp = t0 * (1.0 - it / iters) + 1e-4
            a = np.random.randint(n_sym)
            old = key[a]
            new_l = np.random.randint(26)
            if new_l == old or counts[a] == 0:
                continue
            tick += 1
            nw = 0
            for q in range(start[a], start[a + 1]):
                p = pos[q]
                for st in range(max(0, p - 4), min(n - 5, p) + 1):
                    if stamp[st] != tick:
                        stamp[st] = tick
                        windows[nw] = st
                        nw += 1
            before = 0.0
            for j in range(nw):
                st = windows[j]
                before += table[plain[st] * 456976 + plain[st + 1] * 17576 + plain[st + 2] * 676 + plain[st + 3] * 26 + plain[st + 4]]
            for q in range(start[a], start[a + 1]):
                plain[pos[q]] = new_l
            after = 0.0
            for j in range(nw):
                st = windows[j]
                after += table[plain[st] * 456976 + plain[st + 1] * 17576 + plain[st + 2] * 676 + plain[st + 3] * 26 + plain[st + 4]]
            c = float(counts[a])
            chi = ((lc[old] - c - expected[old]) ** 2 - (lc[old] - expected[old]) ** 2) / expected[old] + ((lc[new_l] + c - expected[new_l]) ** 2 - (lc[new_l] - expected[new_l]) ** 2) / expected[new_l]
            d = after - before - w * chi
            if d >= 0 or np.random.random() < np.exp(d / temp):
                key[a] = new_l
                lc[old] -= c
                lc[new_l] += c
                cur += d
                if cur > best:
                    best, best_key = cur, key.copy()
            else:
                for q in range(start[a], start[a + 1]):
                    plain[pos[q]] = old
    return best_key, best


__all__ = ["table5", "score5", "anneal5", "letters"]
