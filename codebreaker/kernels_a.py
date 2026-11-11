"""Numba loops for alphabets of any size A (Round 86): quadgram score and substitution annealing.
Quadgram index: ((a*A + b)*A + c)*A + d, as built in alphabets.py."""
import numpy as np
from numba import njit


@njit(cache=True)
def quad_score_a(t, table, A):
    s = 0.0
    for i in range(len(t) - 3):
        s += table[((t[i] * A + t[i + 1]) * A + t[i + 2]) * A + t[i + 3]]
    return s


@njit(cache=True)
def _delta_ok(d, temp):
    return d >= 0 or np.random.random() < np.exp(d / temp)


@njit(cache=True)
def anneal_sub_a(ct, A, table, iters, restarts, seed, t0):
    """Simple substitution over an alphabet of A letters: key[c] = plaintext letter for ciphertext letter c."""
    np.random.seed(seed)
    n = len(ct)
    best = -1e18
    best_key = np.arange(A).astype(np.int32)
    plain = np.zeros(n, dtype=np.int32)
    for _ in range(restarts):
        key = np.random.permutation(A).astype(np.int32)
        for i in range(n):
            plain[i] = key[ct[i]]
        cur = quad_score_a(plain, table, A)
        for it in range(iters):
            temp = t0 * (1.0 - it / iters) + 1e-6
            a, b = np.random.randint(A), np.random.randint(A)
            if a == b:
                continue
            key[a], key[b] = key[b], key[a]
            for i in range(n):
                plain[i] = key[ct[i]]
            new = quad_score_a(plain, table, A)
            if _delta_ok(new - cur, temp):
                cur = new
                if cur > best:
                    best = cur
                    best_key = key.copy()
            else:
                key[a], key[b] = key[b], key[a]
    return best_key, best
