"""Numba annealing for archive ciphers (Round 88): each symbol stands for a letter, for nothing (a null), or for a
whole code word (a nomenclator entry). Values: 0-25 letters, 26 null, 27+ code words (expansions in flat arrays).

The plaintext changes length as symbols become nulls or words, so the score must not reward short output: it is the
quadgram excess over the language's mean, sum(q - mu), with a chi-square penalty on letter frequencies (w) against
homophonic overfitting. A letter that fits worse than average lowers the score, so a symbol becomes a null only when
deleting its occurrences makes the rest read better than the average text."""
import numpy as np
from numba import njit


@njit(cache=True)
def _expand(ct, key, starts, lens, flat, out, src):
    """Plaintext letters into out; src[i] = the token each letter came from, negative for letters of a code word."""
    n = 0
    for i in range(len(ct)):
        v = key[ct[i]]
        for j in range(lens[v]):
            out[n] = flat[starts[v] + j]
            src[n] = i if lens[v] == 1 else -1 - i
            n += 1
    return n


@njit(cache=True)
def _score(p, src, n, table, mu, letter, w):
    """Quadgram excess over mu; quadgrams inside one code word count as neutral (a word must earn its place by
    fitting its context, not by its own spelling), and code-word letters stay out of the frequency check."""
    s = 0.0
    for i in range(n - 3):
        if src[i] < 0 and src[i] == src[i + 3]:
            continue
        s += table[p[i] * 17576 + p[i + 1] * 676 + p[i + 2] * 26 + p[i + 3]] - mu
    if w > 0 and n > 0:
        c = np.zeros(26)
        m = 0
        for i in range(n):
            if src[i] >= 0:
                c[p[i]] += 1
                m += 1
        for k in range(26):
            e = m * letter[k] + 1e-9
            s -= w * (c[k] - e) ** 2 / e
    return s


@njit(cache=True)
def anneal_nom(ct, n_sym, starts, lens, flat, n_vals, allow_null, table, mu, letter, w, iters, restarts, seed, t0, fixed, cap):
    """fixed[s] >= 0 pins symbol s to that value (e.g. a detected word divider as a null). cap[v]: the most occurrences a
    symbol may have to take value v (a code word as often as the word itself, a null rarely). Returns (key, score)."""
    np.random.seed(seed)
    count = np.zeros(n_sym, dtype=np.int64)
    for i in range(len(ct)):
        count[ct[i]] += 1
    out = np.zeros(len(ct) * 12 + 16, dtype=np.int32)
    src = np.zeros(len(ct) * 12 + 16, dtype=np.int64)
    best = -1e18
    best_key = np.zeros(n_sym, dtype=np.int32)
    for _ in range(restarts):
        key = np.random.randint(0, 26, n_sym).astype(np.int32)
        for s in range(n_sym):
            if fixed[s] >= 0:
                key[s] = fixed[s]
        n = _expand(ct, key, starts, lens, flat, out, src)
        cur = _score(out, src, n, table, mu, letter, w)
        for it in range(iters):
            temp = t0 * (1.0 - it / iters) + 1e-6
            s = np.random.randint(n_sym)
            if fixed[s] >= 0:
                continue
            old = key[s]
            r = np.random.random()
            if r < 0.85 or n_vals <= 26:
                key[s] = np.random.randint(26)
            elif r < 0.93 and allow_null:
                key[s] = 26
            elif n_vals > 27:
                key[s] = 27 + np.random.randint(n_vals - 27)
            else:
                key[s] = np.random.randint(26)
            if key[s] == old or count[s] > cap[key[s]]:
                key[s] = old
                continue
            n = _expand(ct, key, starts, lens, flat, out, src)
            new = _score(out, src, n, table, mu, letter, w)
            if new >= cur or np.random.random() < np.exp((new - cur) / temp):
                cur = new
                if cur > best:
                    best = cur
                    best_key = key.copy()
            else:
                key[s] = old
    return best_key, best
