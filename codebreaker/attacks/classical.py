"""General solvers for classical ciphers. Each returns {plaintext, key, score, method}."""
import numpy as np

from .. import kernels as K
from ..analysis import ic, likely_period
from ..languages import corpus_text, keywords, model, score
from ..text import A, keyed_alphabet, letters, to_ints, to_text


def result(plain, key, method, lang="en"):
    return {"plaintext": plain, "key": key, "method": method, "score": round(score(plain, lang), 3)}


def keyspace(decrypt, keys, lang="en", method="exhaustive key search"):
    """Try each key dict; keep the decryption that reads most like the language."""
    best, best_key, best_s = "", None, -1e18
    for k in keys:
        try:
            p = decrypt(**k)
        except (ValueError, ZeroDivisionError, IndexError):
            continue
        s = score(p, lang)
        if s > best_s:
            best, best_key, best_s = p, k, s
    return result(best, best_key, method, lang)


def word_keys(name="keyword", lang="en", n=2500, extra=None):
    for w in keywords(lang, n, 4):
        yield {name: w, **(extra or {})}


def symbols_to_ints(symbols):
    alpha = sorted(set(symbols))
    idx = {s: i for i, s in enumerate(alpha)}
    return np.array([idx[s] for s in symbols], dtype=np.int32), alpha


def solve_symbols(symbols, lang="en", homophonic=False, iters=None, restarts=None, seed=1, t0=None, w=None):
    """Solve a symbol->letter substitution by simulated annealing."""
    ct, alpha = symbols_to_ints(symbols)
    homophonic = homophonic or len(alpha) > 26
    m = model(lang)
    if homophonic:
        key, _ = K.anneal_homophonic(ct, len(alpha), m["table"], m["letter"], 2.0 if w is None else w, iters or 3000000, restarts or 6, seed, 3.0 * (len(ct) / 400) ** 0.5 if t0 is None else t0)
    else:
        key, _ = K.anneal_mapping(ct, len(alpha), m["table"], iters or 60000, restarts or 8, seed, False, 3.0 if t0 is None else t0, m["letter"], w or 0.0)
    plain = to_text(key[ct])
    return result(plain, {str(a): A[int(key[i])] for i, a in enumerate(alpha)}, "simulated annealing on quadgrams", lang)


def substitution(ct, lang="en"):
    return solve_symbols(letters(ct), lang)


def pairs(text):
    d = "".join(c for c in text if not c.isspace())
    return [d[i:i + 2] for i in range(0, len(d) - 1, 2)]


def periodic(ct, decrypt_ints, lang="en", shifts=26, max_period=24, method="period from IC, then column search"):
    """Vigenere-family attack: pick the period by IC, set each key letter by coordinate ascent."""
    t, table, letter = to_ints(ct), model(lang)["table"], np.log(model(lang)["letter"] + 1e-6)
    best = (-1e18, None, None)
    for p in likely_period(t, max_period):
        key = np.zeros(p, dtype=np.int32)
        for col in range(p):  # initialise by single-letter fit
            sc = []
            for k in range(shifts):
                trial = np.zeros(p, dtype=np.int32)
                trial[col] = k
                sc.append(letter[decrypt_ints(t, trial)[col::p]].sum())
            key[col] = int(np.argmax(sc))
        cur = K.quad_score(decrypt_ints(t, key), table)
        for _ in range(4):
            changed = False
            for col in range(p):
                for k in range(shifts):
                    old = key[col]
                    key[col] = k
                    s = K.quad_score(decrypt_ints(t, key), table)
                    if s > cur:
                        cur, changed = s, True
                    else:
                        key[col] = old
            if not changed:
                break
        norm = cur / max(len(t) - 3, 1) - 0.002 * p  # mild preference for short periods
        if norm > best[0]:
            best = (norm, key.copy(), p)
    _, key, p = best
    return result(to_text(decrypt_ints(t, key)), {"key": to_text(key), "period": p}, method, lang)


def autokey(ct, lang="en"):
    t, table = to_ints(ct), model(lang)["table"]
    best = (-1e18, None)
    for p in range(1, 16):
        key = np.zeros(p, dtype=np.int32)
        cur = K.quad_score(K.autokey_decrypt(t, key), table)
        for _ in range(6):
            for col in range(p):
                for k in range(26):
                    old, key[col] = key[col], k
                    s = K.quad_score(K.autokey_decrypt(t, key), table)
                    if s > cur:
                        cur = s
                    else:
                        key[col] = old
        if cur > best[0]:
            best = (cur, key.copy())
    return result(to_text(K.autokey_decrypt(t, best[1])), {"key": to_text(best[1])}, "per-letter key climb over periods 1-15", lang)


def running_key(ct, lang="en"):
    t, table = to_ints(ct), model(lang)["table"]
    book = to_ints(corpus_text(lang))
    s = K.running_scan(t, book, table)
    off = int(np.argmax(s))
    return result(to_text((t - book[off:off + len(t)]) % 26), {"book_offset": off, "key": to_text(book[off:off + 30]) + "..."},
                  "slid the ciphertext along a candidate key book", lang)


def quagmire(ct, decrypt_fn, lang="en"):
    """Keyed-alphabet Vigenere: guess the alphabet keyword, then solve the period by column fit."""
    t = to_ints(ct)
    letter = np.log(model(lang)["letter"] + 1e-6)
    p = likely_period(t, 20)[0]
    best = (-1e18, None)
    for word in keywords(lang, 1500, 4) + ["KRYPTOS"]:
        alpha = np.array([ord(c) - 65 for c in keyed_alphabet(word)])
        idx = np.argsort(alpha)  # position of each letter in the keyed alphabet
        pos = idx[t]
        key_idx = []
        total = 0.0
        for col in range(p):
            cands = [letter[alpha[(pos[col::p] - k) % 26]].sum() for k in range(26)]
            k = int(np.argmax(cands))
            key_idx.append(k)
            total += cands[k]
        if total > best[0]:
            best = (total, (word, "".join(A[alpha[k]] for k in key_idx)))
    word, key = best[1]
    return result(decrypt_fn(ct, alphabet=word, key=key), {"alphabet": word, "key": key}, f"alphabet dictionary with period {p}", lang)


def playfair(ct, lang="en"):
    t = to_ints(ct)
    sq, _ = K.anneal_playfair(t, model(lang)["table"], 1000000, 4, 7, 12.0)
    return result(to_text(K.playfair_decrypt(t, sq)), {"square": to_text(sq)}, "simulated annealing on the 5x5 square", lang)


def columnar_search(ct, lang="en", max_k=14):
    t, table = to_ints(ct), model(lang)["table"]
    best = (-1e18, None)
    for k in range(2, max_k + 1):
        perm, s = K.climb_columnar(t, k, table, 40000, 12, k)
        if s > best[0] + 1e-9:
            best = (s, perm.copy())
    perm = best[1]
    return result(to_text(K.columnar_decrypt(t, perm)), {"column_order": [int(x) for x in perm]},
                  "hill climb on column order, key lengths 2-14", lang)


def hill2(ct, lang="en"):
    t = to_ints(ct)
    (a, b, c, d), _ = K.hill2_scan(t, model(lang)["table"])
    n = len(t) - len(t) % 2
    p = t[:n].copy()
    p[::2], p[1::2] = (a * t[:n:2] + b * t[1:n:2]) % 26, (c * t[:n:2] + d * t[1:n:2]) % 26
    return result(to_text(p), {"inverse_matrix": [a, b, c, d]}, "all invertible 2x2 matrices", lang)


__all__ = ["keyspace", "word_keys", "solve_symbols", "substitution", "periodic", "autokey", "running_key",
           "quagmire", "playfair", "columnar_search", "hill2", "pairs", "result", "symbols_to_ints", "ic"]
