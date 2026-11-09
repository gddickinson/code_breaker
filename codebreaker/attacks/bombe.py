"""A Turing-Welchman style bombe: break a plugboard Enigma from a crib, by contradiction."""
import itertools
import random

import numpy as np
from numba import njit

from .. import kernels as K
from ..languages import model
from ..text import A, letters, to_ints, to_text


@njit(cache=True)
def _scramble(c, pos, wires, inv, refl):
    for r in (2, 1, 0):
        c = (wires[r, (c + pos[r]) % 26] - pos[r]) % 26
    c = refl[c]
    for r in (0, 1, 2):
        c = (inv[r, (c + pos[r]) % 26] - pos[r]) % 26
    return c


@njit(cache=True)
def bombe_scan(crib, cipher, wires, notch, refl, anchor):
    """Each start position, and plug guess for the anchor letter, that creates no contradiction."""
    n = len(crib)
    inv = np.zeros((3, 26), dtype=np.int64)
    for r in range(3):
        for i in range(26):
            inv[r, wires[r, i]] = i
    tracks = np.zeros((n, 3), dtype=np.int64)
    stops = []
    plug = np.zeros(26, dtype=np.int64)
    for a in range(26):
        for b in range(26):
            for c0 in range(26):
                pos = np.array([a, b, c0], dtype=np.int64)
                for i in range(n):
                    if pos[1] == notch[1]:
                        pos[0] = (pos[0] + 1) % 26
                        pos[1] = (pos[1] + 1) % 26
                    elif pos[2] == notch[2]:
                        pos[1] = (pos[1] + 1) % 26
                    pos[2] = (pos[2] + 1) % 26
                    tracks[i] = pos
                for guess in range(26):
                    plug[:] = -1
                    plug[anchor], plug[guess] = guess, anchor
                    ok, changed = True, True
                    while ok and changed:
                        changed = False
                        for i in range(n):
                            for x, y in ((crib[i], cipher[i]), (cipher[i], crib[i])):
                                if plug[x] < 0:
                                    continue
                                z = _scramble(plug[x], tracks[i], wires, inv, refl)
                                if plug[y] < 0 and plug[z] < 0:
                                    plug[y], plug[z] = z, y
                                    changed = True
                                elif plug[y] != z or plug[z] != y:
                                    ok = False
                                    break
                            if not ok:
                                break
                    if ok:
                        stops.append((a, b, c0, guess, int((plug >= 0).sum())))
    return stops


def _plugs(crib, cipher, wires, notch, refl, start, anchor, guess):
    n = len(crib)
    inv = np.argsort(wires, axis=1)
    pos, tracks = np.array(start, dtype=np.int64), []
    for _ in range(n):
        if pos[1] == notch[1]:
            pos[0], pos[1] = (pos[0] + 1) % 26, (pos[1] + 1) % 26
        elif pos[2] == notch[2]:
            pos[1] = (pos[1] + 1) % 26
        pos[2] = (pos[2] + 1) % 26
        tracks.append(pos.copy())
    plug = [-1] * 26
    plug[anchor], plug[guess] = guess, anchor
    for _ in range(n + 2):
        for i in range(n):
            for x, y in ((int(crib[i]), int(cipher[i])), (int(cipher[i]), int(crib[i]))):
                if plug[x] >= 0 and plug[y] < 0:
                    z = int(_scramble(plug[x], tracks[i], wires, inv, refl))
                    plug[y], plug[z] = z, y
    return plug


def _finish(ct, wires, notch, refl, start, plug, table):
    """Complete the board: unset letters default to themselves, then try each remaining pair."""
    p = np.array([v if v >= 0 else i for i, v in enumerate(plug)], dtype=np.int32)
    ring = np.zeros(3, dtype=np.int32)
    s = np.array(start, dtype=np.int32)
    best = K.quad_score(K.enigma_run(ct, wires, notch, refl, ring, s, p), table)
    open_l = [i for i, v in enumerate(plug) if v < 0]
    improved = True
    while improved:
        improved = False
        for a, b in itertools.combinations(open_l, 2):
            if p[a] != a or p[b] != b:
                continue
            q = p.copy()
            q[a], q[b] = b, a
            v = K.quad_score(K.enigma_run(ct, wires, notch, refl, ring, s, q), table)
            if v > best:
                best, p, improved = v, q, True
    return best, p


def attack(ciphertext: str, crib_text: str, offset: int = 0, rotor_sets=None, lang: str = "en") -> dict:
    """Crib must already be free of self-encryptions; the rotor ring settings are assumed to be A."""
    from ..ciphers.machines import REFLECTOR_B, _setup

    ct, crib = to_ints(ciphertext), to_ints(crib_text)
    table = model(lang)["table"]
    head = ct[offset: offset + len(crib)]
    anchor = int(np.bincount(np.concatenate((crib, head)), minlength=26).argmax())
    results, tested, stops_total = [], 0, 0
    refl = REFLECTOR_B.astype(np.int64)
    for order in rotor_sets or itertools.permutations(["I", "II", "III"]):
        w, n = _setup(" ".join(order))
        w64, n64 = w.astype(np.int64), n.astype(np.int64)
        stops = bombe_scan(crib, head, w64, n64, refl, anchor)
        tested += 17576
        stops_total += len(stops)
        for a, b, c, guess, known in stops[:400]:
            plug = _plugs(crib, head, w64, n64, refl, (a, b, c), anchor, guess)
            # With a crib offset the search starts at the crib; rewinding is handled for offset 0 only.
            score_, p = _finish(ct, w, n, REFLECTOR_B, (a, b, c), plug, table)
            results.append((float(score_), " ".join(order), A[a] + A[b] + A[c], p))
    results.sort(key=lambda r: -r[0])
    _, rotors, start, p = results[0]
    w, n = _setup(rotors)
    plain = to_text(K.enigma_run(ct, w, n, REFLECTOR_B, np.zeros(3, dtype=np.int32), to_ints(start).astype(np.int32), p))
    pairs = sorted({"".join(sorted(A[i] + A[int(v)])) for i, v in enumerate(p) if int(v) != i})
    return {"plaintext": plain, "rotors": rotors, "start": start, "plugboard": pairs, "positions_tested": tested, "stops": stops_total}


def demo(seed: int = 1) -> dict:
    from ..ciphers.base import DEMO_PLAIN
    from ..ciphers.machines import enigma

    r = random.Random(seed)
    rotors = r.sample(["I", "II", "III"], 3)
    start = "".join(r.choice(A) for _ in range(3))
    alpha = r.sample(A, 16)
    plug = [alpha[i] + alpha[i + 1] for i in range(0, 16, 2)]
    plain = letters(DEMO_PLAIN)
    ct = enigma(plain, " ".join(rotors), "AAA", start, " ".join(plug))
    crib = plain[:32]
    res = attack(ct, crib, 0)
    return {"title": "Bombe search", "rotors": " ".join(rotors), "start": start, "plugboard": sorted("".join(sorted(p)) for p in plug), "crib": crib, "ciphertext": ct, "truth": plain, **{("found_" + k): v for k, v in res.items()},
            "success": res["plaintext"] == plain, "accuracy": round(float(np.mean([a == b for a, b in zip(res["plaintext"], plain)])), 3)}
