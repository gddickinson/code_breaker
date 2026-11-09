"""Annealing with a compiled word model: each key is scored by its best split into dictionary words."""
import numpy as np
from numba import njit

from .languages import model


def build_trie(lang="en", top=25000, max_len=16):
    m = model(lang)
    words = [(str(w), float(np.log10(f))) for w, f in zip(m["words"][:top], m["word_freq"][:top]) if 2 <= len(str(w)) <= max_len or str(w) in ("A", "I")]
    nodes = 1 + sum(len(w) for w, _ in words)
    child = np.full((nodes, 26), -1, dtype=np.int32)
    value = np.full(nodes, -1e9, dtype=np.float64)
    used = 1
    for w, lp in words:
        n = 0
        for ch in w:
            c = ord(ch) - 65
            if child[n, c] < 0:
                child[n, c] = used
                used += 1
            n = child[n, c]
        value[n] = max(value[n], lp)
    return child[:used], value[:used]


@njit(cache=True)
def word_dp(p, child, value, unk):
    n = len(p)
    best = np.full(n + 1, -1e18)
    best[0] = 0.0
    for i in range(n):
        b = best[i]
        if b + unk > best[i + 1]:
            best[i + 1] = b + unk
        node = 0
        j = i
        while j < n:
            node = child[node, p[j]]
            if node < 0:
                break
            v = value[node]
            if v > -1e8 and b + v > best[j + 1]:
                best[j + 1] = b + v
            j += 1
    return best[n]


@njit(cache=True)
def anneal_word(ct, n_sym, child, value, unk, iters, seed, t0, start_key, letter, w):
    np.random.seed(seed)
    key = start_key.copy()
    n = len(ct)
    plain = np.zeros(n, dtype=np.int32)
    for i in range(n):
        plain[i] = key[ct[i]]
    exp = n * letter + 1e-9
    lc = np.bincount(plain, minlength=26).astype(np.float64)
    cur = word_dp(plain, child, value, unk) - w * float((((lc - exp) ** 2) / exp).sum())
    best, best_key = cur, key.copy()
    for it in range(iters):
        temp = t0 * (1.0 - it / iters) + 1e-3
        a = np.random.randint(n_sym)
        old = key[a]
        new = np.random.randint(26)
        if new == old:
            continue
        key[a] = new
        for i in range(n):
            plain[i] = key[ct[i]]
        lc = np.bincount(plain, minlength=26).astype(np.float64)
        s = word_dp(plain, child, value, unk) - w * float((((lc - exp) ** 2) / exp).sum())
        d = s - cur
        if d >= 0 or np.random.random() < np.exp(d / temp):
            cur = s
            if cur > best:
                best, best_key = cur, key.copy()
        else:
            key[a] = old
    return best_key, best
