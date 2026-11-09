"""K4 under two layers: columnar transposition with a repeating key, plus autokey and Hill tests."""
import itertools
import random
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from numba import njit

from ..kernels import columnar_decrypt
from ..languages import model
from ..text import A, keyed_alphabet, to_ints
from .kryptos import CRIBS, sections


def crib_arrays():
    pos, plain = [], []
    for start, crib in CRIBS.items():
        for i, c in enumerate(crib):
            pos.append(start + i)
            plain.append(ord(c) - 65)
    return np.array(pos, dtype=np.int64), np.array(plain, dtype=np.int32)


def alpha_table(word):
    a = keyed_alphabet(word) if word else A
    idx = np.zeros(26, dtype=np.int32)
    for i, c in enumerate(a):
        idx[ord(c) - 65] = i
    return idx


@njit(cache=True)
def _key(c, p, variant):
    return (c - p) % 26 if variant == 0 else ((c + p) % 26 if variant == 1 else (p - c) % 26)


@njit(cache=True)
def scan_perms(ct, perms, pos, plain, idx, variant, period, mode):
    """Return (permutation row, comparisons) for every order consistent with the cribs."""
    n, w = len(ct), perms.shape[1]
    rows, extra = n // w, n % w
    hits, comps_out = [], []
    inv = np.zeros(n, dtype=np.int64)
    seen = np.full(period, -1, dtype=np.int32)
    for r in range(perms.shape[0]):
        p = 0
        for c in perms[r]:
            h = rows + (1 if c < extra else 0)
            for row in range(h):
                inv[row * w + c] = p
                p += 1
        seen[:] = -1
        comps, bad = 0, False
        for t in range(len(pos)):
            j = inv[pos[t]]
            k = _key(idx[ct[j]], idx[plain[t]], variant)
            at = (pos[t] if mode == 0 else j) % period
            if seen[at] < 0:
                seen[at] = k
            else:
                comps += 1
                if seen[at] != k:
                    bad = True
                    break
        if not bad:
            hits.append(r)
            comps_out.append(comps)
    return hits, comps_out


def perms_of(w):
    return np.array(list(itertools.permutations(range(w))), dtype=np.int64)


def layered_job(a):
    ct, w, word, variant, period, mode = a
    pos, plain = crib_arrays()
    perms = perms_of(w)
    hits, comps = scan_perms(ct, perms, pos, plain, alpha_table(word), variant, period, mode)
    real = [(int(h), int(c)) for h, c in zip(hits, comps) if c >= 6]
    return {"width": w, "alphabet": word or "standard", "variant": ["vigenere", "beaufort", "variant"][variant], "period": period, "order": ["key then transpose", "transpose then key"][mode], "orders_tested": len(perms), "survivors": len(real), "expected_by_chance": float(sum(26.0 ** -c for _, c in real)) if real else 0.0, "sample": [[int(x) for x in perms[h]] for h, _ in real[:3]], "min_comparisons": min((c for _, c in real), default=None)}


def layered(ct, widths=range(2, 10), periods=range(1, 13), workers=5):
    jobs = [(ct, w, word, v, p, m) for w in widths for word in ("", "KRYPTOS") for v in range(3) for p in periods for m in range(2)]
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(layered_job, jobs, chunksize=4))


def autokey_tests(ct):
    """A plaintext or ciphertext autokey with lag L: which lags do the cribs allow?"""
    pos, plain = crib_arrays()
    known = {int(p): int(v) for p, v in zip(pos, plain)}
    out = {"plaintext_autokey": 0, "ciphertext_autokey": 0, "models": 0, "untestable": []}
    for word in ("", "KRYPTOS"):
        idx = alpha_table(word)
        for variant in range(3):
            for lag in range(1, 49):
                out["models"] += 1
                bad_c = comps_c = bad_p = comps_p = 0
                for p, v in known.items():
                    if p < lag:
                        continue
                    c = int(idx[ct[p]])
                    k_c = int(_key(c, int(idx[v]), variant))
                    comps_c += 1
                    bad_c += k_c != int(idx[ct[p - lag]])
                    if p - lag in known:
                        comps_p += 1
                        bad_p += k_c != int(idx[known[p - lag]])
                out["ciphertext_autokey"] += comps_c > 0 and bad_c == 0
                out["plaintext_autokey"] += comps_p > 0 and bad_p == 0
                if comps_p == 0:
                    out["untestable"].append(lag)
    out["untestable"] = sorted(set(out["untestable"]))
    return out


def hill_test(ct):
    pos, plain = crib_arrays()
    known = {int(p): int(v) for p, v in zip(pos, plain)}
    feasible = 0
    for phase in (0, 1):
        pairs = [((ct[i], ct[i + 1]), (known[i], known[i + 1])) for i in range(phase, len(ct) - 1, 2) if i in known and i + 1 in known]
        for a, b in itertools.product(range(26), repeat=2):
            if all((a * p0 + b * p1) % 26 == c0 for (c0, _), (p0, p1) in pairs):
                for c, d in itertools.product(range(26), repeat=2):
                    det = (a * d - b * c) % 26
                    if det % 2 and det != 13 and all((c * p0 + d * p1) % 26 == c1 for (_, c1), (p0, p1) in pairs):
                        feasible += 1
    return {"invertible_2x2_keys_consistent": feasible}


def self_encryption(ct):
    pos, plain = crib_arrays()
    return [int(p) for p, v in zip(pos, plain) if ct[p] == v]


def control(seed=3):
    """Plant a width-7, period-5 KRYPTOS layered cipher using K4's clue positions."""
    from ..validation import sample_plaintext
    r = random.Random(seed)
    pos, _ = crib_arrays()
    pt = list(sample_plaintext(97, "en", seed))
    for start, crib in CRIBS.items():
        pt[start:start + len(crib)] = crib
    idx = alpha_table("KRYPTOS")
    alpha = keyed_alphabet("KRYPTOS")
    key = [r.randrange(26) for _ in range(5)]
    v = [alpha[(idx[ord(c) - 65] + key[i % 5]) % 26] for i, c in enumerate(pt)]
    perm = r.sample(range(7), 7)
    n, w = 97, 7
    ct = []
    for c in perm:
        ct += v[c::w]
    ct = to_ints("".join(ct))
    assert "".join(A[i] for i in columnar_decrypt(ct, np.array(perm, dtype=np.int64))) == "".join(v)
    hit = layered_job((ct, 7, "KRYPTOS", 0, 5, 0))
    return {"planted_order": perm, "survivors": hit["survivors"], "found": perm in [list(s) for s in hit["sample"]], "sample": hit["sample"]}


def run() -> dict:
    ct = to_ints(sections()["K4"])
    rows = layered(ct)
    survivors = [r for r in rows if r["survivors"]]
    return {"id": "kryptos_layers", "control": control(), "models": len(rows), "orders_tested": int(sum(r["orders_tested"] for r in rows)), "survivors_total": int(sum(r["survivors"] for r in rows)), "expected_by_chance": sum(r["expected_by_chance"] for r in rows), "top": sorted(survivors, key=lambda r: -(r["min_comparisons"] or 0))[:25],
            "autokey": autokey_tests(ct), "hill": hill_test(ct), "self_encryption_positions": self_encryption(ct)}
