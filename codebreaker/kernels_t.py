"""Numba hill-climbing for columnar transposition keys wider than 7 (irregular last row), both directions."""
import numpy as np
from numba import njit

from .kernels import columnar_decrypt, quad_score


@njit(cache=True)
def columnar_encrypt(pt, perm):
    """Columns of the row-written text, read in the order perm (the inverse of columnar_decrypt)."""
    n, k = len(pt), len(perm)
    out = np.zeros(n, dtype=np.int32)
    pos = 0
    for c in perm:
        for i in range(c, n, k):
            out[pos] = pt[i]
            pos += 1
    return out


@njit(cache=True)
def _apply(ct, perm, inverse):
    return columnar_encrypt(ct, perm) if inverse else columnar_decrypt(ct, perm)


@njit(cache=True)
def _neighbour(perm):
    k = len(perm)
    new_p = perm.copy()
    a, b = np.random.randint(k), np.random.randint(k)
    if a > b:
        a, b = b, a
    r = np.random.random()
    if r < 0.45:
        new_p[a], new_p[b] = perm[b], perm[a]
    elif r < 0.7:  # move one column to another place
        v = perm[a]
        j = 0
        for i in range(k):
            if i != a:
                new_p[j] = perm[i]
                j += 1
        for i in range(k - 1, b, -1):
            new_p[i] = new_p[i - 1]
        new_p[b] = v
    elif r < 0.85:  # reverse a stretch
        for i in range(b - a + 1):
            new_p[a + i] = perm[b - i]
    else:  # rotate: a key started at the wrong column
        for i in range(k):
            new_p[i] = perm[(i + a + 1) % k]
    return new_p


@njit(cache=True)
def climb_wide(ct, k, table, iters, restarts, seed, inverse):
    """Best key of width k by restarted hill-climbing with mild annealing; returns (perm, quadgram sum)."""
    np.random.seed(seed)
    best_perm = np.arange(k)
    best = -1e18
    for _ in range(restarts):
        perm = np.random.permutation(k)
        cur = quad_score(_apply(ct, perm, inverse), table)
        top, top_p = cur, perm.copy()
        temp = 2.0
        for i in range(iters):
            new_p = _neighbour(perm)
            s = quad_score(_apply(ct, new_p, inverse), table)
            if s > cur or np.random.random() < np.exp((s - cur) / temp):
                cur, perm = s, new_p
                if cur > top:
                    top, top_p = cur, perm.copy()
            temp = max(0.05, 2.0 * (1.0 - i / iters))
        if top > best:
            best, best_perm = top, top_p
    return best_perm, best


@njit(cache=True)
def _qs_mapped(t, key, table):
    m = np.empty(len(t), dtype=np.int32)
    for i in range(len(t)):
        m[i] = key[t[i]]
    return quad_score(m, table)


@njit(cache=True)
def anneal_joint(ct, k, table, iters, restarts, seed, inverse):
    """Anneal a columnar key of width k and a one-to-one substitution together; returns (perm, key, score)."""
    np.random.seed(seed)
    best_p, best_k, best = np.arange(k), np.arange(26).astype(np.int32), -1e18
    for _ in range(restarts):
        perm = np.random.permutation(k)
        key = np.random.permutation(26).astype(np.int32)
        t = _apply(ct, perm, inverse)
        cur = _qs_mapped(t, key, table)
        for i in range(iters):
            temp = max(0.2, 8.0 * (1.0 - i / iters))
            if np.random.random() < 0.25:
                new_p = _neighbour(perm)
                nt = _apply(ct, new_p, inverse)
                s = _qs_mapped(nt, key, table)
                if s >= cur or np.random.random() < np.exp((s - cur) / temp):
                    perm, t, cur = new_p, nt, s
            else:
                a, b = np.random.randint(26), np.random.randint(26)
                key[a], key[b] = key[b], key[a]
                s = _qs_mapped(t, key, table)
                if s >= cur or np.random.random() < np.exp((s - cur) / temp):
                    cur = s
                else:
                    key[a], key[b] = key[b], key[a]
            if cur > best:
                best, best_p, best_k = cur, perm.copy(), key.copy()
    return best_p, best_k, best
