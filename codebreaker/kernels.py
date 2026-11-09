"""Numba-compiled inner loops: scoring and stochastic key search."""
import numpy as np
from numba import njit


@njit(cache=True)
def quad_score(t, table):
    """Sum of quadgram log-probabilities over an int array of letters 0-25."""
    s = 0.0
    for i in range(len(t) - 3):
        s += table[t[i] * 17576 + t[i + 1] * 676 + t[i + 2] * 26 + t[i + 3]]
    return s


@njit(cache=True)
def fit_score(p, table, letter, w):
    """Quadgram score minus w * chi-square distance from expected letter frequencies.

    The penalty stops homophonic search overfitting: with many free symbols, quadgram
    score alone prefers repetitive THE-like text over the true plaintext.
    """
    s = quad_score(p, table)
    if w > 0:
        n = len(p)
        c = np.bincount(p, minlength=26)
        s -= w * float((((c - n * letter) ** 2) / (n * letter + 1e-9)).sum())
    return s


@njit(cache=True)
def anneal_mapping(ct, n_sym, table, iters, restarts, seed, homophonic, t0, letter, w):
    """Search symbol->letter maps. homophonic=False keeps the map one-to-one."""
    np.random.seed(seed)
    best_key = np.zeros(n_sym, dtype=np.int32)
    best = -1e18
    n = len(ct)
    plain = np.zeros(n, dtype=np.int32)
    for _ in range(restarts):
        if homophonic:
            key = np.random.randint(0, 26, n_sym).astype(np.int32)
        else:
            key = np.random.permutation(26).astype(np.int32)
        for i in range(n):
            plain[i] = key[ct[i]]
        cur = fit_score(plain, table, letter, w)
        for it in range(iters):
            temp = t0 * (1.0 - it / iters) + 1e-6
            if homophonic:
                a = np.random.randint(n_sym)
                old = key[a]
                key[a] = np.random.randint(26)
                b = -1
            else:
                a, b = np.random.randint(len(key)), np.random.randint(len(key))
                key[a], key[b] = key[b], key[a]
                old = 0
            for i in range(n):
                plain[i] = key[ct[i]]
            new = fit_score(plain, table, letter, w)
            d = new - cur
            if d >= 0 or np.random.random() < np.exp(d / temp):
                cur = new
                if cur > best:
                    best = cur
                    best_key = key[:n_sym].copy() if homophonic else key.copy()
            elif homophonic:
                key[a] = old
            else:
                key[a], key[b] = key[b], key[a]
    return best_key, best




@njit(cache=True)
def columnar_decrypt(ct, perm):
    """perm[i] = the column read i-th during encryption (irregular last row)."""
    n, k = len(ct), len(perm)
    rows, extra = n // k, n % k
    out = np.zeros(n, dtype=np.int32)
    pos = 0
    for c in perm:
        h = rows + (1 if c < extra else 0)
        for r in range(h):
            out[r * k + c] = ct[pos]
            pos += 1
    return out


@njit(cache=True)
def climb_columnar(ct, k, table, iters, restarts, seed):
    np.random.seed(seed)
    best_perm = np.arange(k)
    best = -1e18
    for _ in range(restarts):
        perm = np.random.permutation(k)
        cur = quad_score(columnar_decrypt(ct, perm), table)
        stale = 0
        for _i in range(iters):
            new_p = perm.copy()
            a, b = np.random.randint(k), np.random.randint(k)
            if np.random.random() < 0.6:
                new_p[a], new_p[b] = new_p[b], new_p[a]
            else:  # rotate a block: handles shifted keys
                new_p = np.concatenate((perm[a:], perm[:a]))
            s = quad_score(columnar_decrypt(ct, new_p), table)
            if s > cur:
                cur, perm, stale = s, new_p, 0
            else:
                stale += 1
                if stale > 40 * k * k:
                    break
        if cur > best:
            best, best_perm = cur, perm.copy()
    return best_perm, best


@njit(cache=True)
def playfair_decrypt(ct, sq):
    pos = np.zeros(26, dtype=np.int32)
    for i in range(25):
        pos[sq[i]] = i
    out = ct.copy()
    for i in range(0, len(ct) - 1, 2):
        p, q = pos[ct[i]], pos[ct[i + 1]]
        r1, c1, r2, c2 = p // 5, p % 5, q // 5, q % 5
        if r1 == r2:
            c1, c2 = (c1 + 4) % 5, (c2 + 4) % 5
        elif c1 == c2:
            r1, r2 = (r1 + 4) % 5, (r2 + 4) % 5
        else:
            c1, c2 = c2, c1
        out[i], out[i + 1] = sq[r1 * 5 + c1], sq[r2 * 5 + c2]
    return out


@njit(cache=True)
def anneal_playfair(ct, table, iters, restarts, seed, t0=4.0):
    np.random.seed(seed)
    letters = np.array([x for x in range(26) if x != 9], dtype=np.int32)  # J merged into I
    best_sq, best = letters.copy(), -1e18
    for _ in range(restarts):
        sq = np.random.permutation(letters)
        cur = quad_score(playfair_decrypt(ct, sq), table)
        for it in range(iters):
            temp = t0 * (1 - it / iters) + 1e-3
            new = sq.copy()
            m = np.random.random()
            if m < 0.9:
                a, b = np.random.randint(25), np.random.randint(25)
                new[a], new[b] = new[b], new[a]
            elif m < 0.95:
                a, b = np.random.randint(5), np.random.randint(5)
                for c in range(5):
                    new[a * 5 + c], new[b * 5 + c] = sq[b * 5 + c], sq[a * 5 + c]
            else:
                a, b = np.random.randint(5), np.random.randint(5)
                for r in range(5):
                    new[r * 5 + a], new[r * 5 + b] = sq[r * 5 + b], sq[r * 5 + a]
            s = quad_score(playfair_decrypt(ct, new), table)
            if s >= cur or np.random.random() < np.exp((s - cur) / temp):
                sq, cur = new, s
                if cur > best:
                    best, best_sq = cur, sq.copy()
    return best_sq, best


@njit(cache=True)
def book_offset_scan(numbers, initials, table, shift_max):
    """Decode a book cipher at each document offset; return the score of every offset."""
    n = len(numbers)
    m = len(initials)
    scores = np.full(shift_max, -1e18)
    buf = np.zeros(n, dtype=np.int32)
    for off in range(shift_max):
        ok = 0
        for i in range(n):
            j = numbers[i] - 1 + off
            if 0 <= j < m:
                buf[ok] = initials[j]
                ok += 1
        if ok >= 0.9 * n:
            scores[off] = quad_score(buf[:ok], table) / max(ok - 3, 1)
    return scores


@njit(cache=True)
def autokey_decrypt(ct, key):
    out = ct.copy()
    k = len(key)
    for i in range(len(ct)):
        shift = key[i] if i < k else out[i - k]
        out[i] = (ct[i] - shift) % 26
    return out


@njit(cache=True)
def running_scan(ct, book, table):
    """Score Vigenere decryption of ct against every offset of a running-key book."""
    n = len(ct)
    scores = np.zeros(len(book) - n)
    for off in range(len(book) - n):
        scores[off] = quad_score((ct - book[off:off + n]) % 26, table)
    return scores


@njit(cache=True)
def hill2_scan(ct, table):
    """Try every invertible 2x2 inverse matrix; return the best one."""
    best, out = -1e18, (1, 0, 0, 1)
    p = ct.copy()
    n = len(ct) - len(ct) % 2
    for a in range(26):
        for b in range(26):
            for c in range(26):
                for d in range(26):
                    det = (a * d - b * c) % 26
                    if det % 2 == 0 or det == 13:
                        continue
                    for i in range(0, n, 2):
                        p[i] = (a * ct[i] + b * ct[i + 1]) % 26
                        p[i + 1] = (c * ct[i] + d * ct[i + 1]) % 26
                    s = quad_score(p[:n], table)
                    if s > best:
                        best, out = s, (a, b, c, d)
    return out, best


@njit(cache=True)
def enigma_run(ct, wires, notch, reflector, ring, start, plug):
    """Enigma I. wires/notch/ring/start ordered left, middle, right."""
    inv = np.zeros((3, 26), dtype=np.int32)
    for r in range(3):
        for i in range(26):
            inv[r, wires[r, i]] = i
    pos = start.copy()
    out = ct.copy()
    for i in range(len(ct)):
        if pos[1] == notch[1]:  # double stepping
            pos[0] = (pos[0] + 1) % 26
            pos[1] = (pos[1] + 1) % 26
        elif pos[2] == notch[2]:
            pos[1] = (pos[1] + 1) % 26
        pos[2] = (pos[2] + 1) % 26
        c = plug[ct[i]]
        for r in (2, 1, 0):
            c = (wires[r, (c + pos[r] - ring[r]) % 26] - pos[r] + ring[r]) % 26
        c = reflector[c]
        for r in (0, 1, 2):
            c = (inv[r, (c + pos[r] - ring[r]) % 26] - pos[r] + ring[r]) % 26
        out[i] = plug[c]
    return out


@njit(cache=True)
def enigma_scan(ct, wires, notch, reflector):
    """Best start position by index of coincidence (the Gillogly ciphertext-only method)."""
    best, best_pos = -1.0, np.zeros(3, dtype=np.int32)
    ring, plug = np.zeros(3, dtype=np.int32), np.arange(26).astype(np.int32)
    n = len(ct)
    for a in range(26):
        for b in range(26):
            for c in range(26):
                s = np.array([a, b, c], dtype=np.int32)
                counts = np.bincount(enigma_run(ct, wires, notch, reflector, ring, s, plug), minlength=26)
                v = float((counts * (counts - 1)).sum()) / (n * (n - 1))
                if v > best:
                    best, best_pos = v, s
    return best_pos, best


@njit(cache=True)
def anneal_homophonic(ct, n_sym, table, letter, w, iters, restarts, seed, t0):
    """Homophonic annealing with incremental scoring: only touched quadgrams are recomputed."""
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
    windows = np.zeros(n * 4 + 4, dtype=np.int64)
    expected = n * letter + 1e-9
    best, best_key, tick = -1e18, np.zeros(n_sym, dtype=np.int32), 0
    plain = np.zeros(n, dtype=np.int32)
    for _ in range(restarts):
        key = np.searchsorted(np.cumsum(letter), np.random.random(n_sym)).astype(np.int32)
        key = np.minimum(key, 25).astype(np.int32)
        for i in range(n):
            plain[i] = key[ct[i]]
        quad = quad_score(plain, table)
        lc = np.bincount(plain, minlength=26).astype(np.float64)
        cur = quad - w * float((((lc - expected) ** 2) / expected).sum())
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
                for st in range(max(0, p - 3), min(n - 4, p) + 1):
                    if stamp[st] != tick:
                        stamp[st] = tick
                        windows[nw] = st
                        nw += 1
            before = 0.0
            for j in range(nw):
                st = windows[j]
                before += table[plain[st] * 17576 + plain[st + 1] * 676 + plain[st + 2] * 26 + plain[st + 3]]
            for q in range(start[a], start[a + 1]):
                plain[pos[q]] = new_l
            after = 0.0
            for j in range(nw):
                st = windows[j]
                after += table[plain[st] * 17576 + plain[st + 1] * 676 + plain[st + 2] * 26 + plain[st + 3]]
            c = float(counts[a])
            chi_d = ((lc[old] - c - expected[old]) ** 2 - (lc[old] - expected[old]) ** 2) / expected[old]
            chi_d += ((lc[new_l] + c - expected[new_l]) ** 2 - (lc[new_l] - expected[new_l]) ** 2) / expected[new_l]
            d = after - before - w * chi_d
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
