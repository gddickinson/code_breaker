"""Rotor and wheel cipher machines, plus book and homophonic systems."""
import itertools
import random

import numpy as np

from .. import kernels as K
from ..attacks import classical as X
from ..languages import ROOT, model
from ..text import A, letters, to_ints, to_text
from .base import Param, add

ROTORS = {"I": ("EKMFLGDQVZNTOWYHXUSPAIBRCJ", "Q"), "II": ("AJDKSIRUXBLHWTMCQGZNPYFVOE", "E"), "III": ("BDFHJLCPRTXVZNYEIWGAKMUSQO", "V"),
          "IV": ("ESOVPZJAYQUIRHXLNFTGKDCMWB", "J"), "V": ("VZBRGITYUPSDNHLXAWMJQOFECK", "Z")}
REFLECTOR_B = to_ints("YRUHQSLDPXNGOKMIEBFZCWVJAT")


def _setup(rotors):
    names = rotors.upper().replace(",", " ").split()
    wires = np.array([to_ints(ROTORS[n][0]) for n in names], dtype=np.int32)
    notch = np.array([A.index(ROTORS[n][1]) for n in names], dtype=np.int32)
    return wires, notch


def _plug(s):
    p = np.arange(26).astype(np.int32)
    for pair in s.upper().split():
        a, b = A.index(pair[0]), A.index(pair[1])
        p[a], p[b] = b, a
    return p


def enigma(t, rotors="I II III", ring="AAA", start="AAA", plugboard=""):
    wires, notch = _setup(rotors)
    return to_text(K.enigma_run(to_ints(t), wires, notch, REFLECTOR_B, to_ints(ring).astype(np.int32), to_ints(start).astype(np.int32), _plug(plugboard)))


def enigma_attack(ct, lang="en"):
    t, table = to_ints(ct), model(lang)["table"]
    best = (-1e18, None)
    for order in itertools.permutations(["I", "II", "III"]):
        wires, notch = _setup(" ".join(order))
        pos, _ = K.enigma_scan(t, wires, notch, REFLECTOR_B)
        s = K.quad_score(K.enigma_run(t, wires, notch, REFLECTOR_B, np.zeros(3, dtype=np.int32), pos, np.arange(26).astype(np.int32)), table)
        if s > best[0]:
            best = (s, (" ".join(order), to_text(pos)))
    rotors, start = best[1]
    return X.result(enigma(ct, rotors, "AAA", start), {"rotors": rotors, "start": start}, "index-of-coincidence scan of rotor orders and start positions", lang)


add(id="enigma", name="Enigma I", family="Machines", era="Germany, 1930s-1945", summary="Three rotors, a reflector and a plugboard.",
    how="Each keypress steps the rotors, including the mechanical double-step, then the current passes through plugboard, rotors, reflector and back. It is reciprocal: the same setting decrypts. Output is checked against the standard test vector AAAAA to BDZGO.",
    weakness="A letter never encrypts to itself, which made cribs at Bletchley Park very powerful. Our demo uses Gillogly's ciphertext-only IC scan over three rotors with no plugboard. A full wartime setup also needs ring settings and plug recovery, or a bombe with a crib.",
    encrypt=enigma, decrypt=enigma, key={"rotors": "I II III", "ring": "AAA", "start": "MCK", "plugboard": "AV BS CG"}, example="Wetterbericht fuer heute",
    params=[Param("rotors", "Rotors left to right, from I to V"), Param("ring", "Ring settings"), Param("start", "Start position"), Param("plugboard", "Plug pairs, e.g. AV BS")],
    attack=enigma_attack, attack_name="IC scan over rotor order and start (no plugboard)",
    keygen=lambda r: {"rotors": " ".join(r.sample(["I", "II", "III"], 3)), "ring": "AAA", "start": "".join(r.choice(A) for _ in range(3)), "plugboard": ""})


def _discs(n=26, seed=1776):
    r = random.Random(seed)
    return ["".join(r.sample(A, 26)) for _ in range(n)]


def _wheel(t, order, offset, sign):
    discs, t = _discs(), letters(t)
    idx = [int(x) for x in str(order).split(",")]
    return "".join(discs[idx[i % len(idx)]][(discs[idx[i % len(idx)]].index(c) + sign * int(offset)) % 26] for i, c in enumerate(t))


def jw_e(t, order="3,1,4,1,5,9,2,6", offset=5):
    return _wheel(t, order, offset, 1)


def jw_d(t, order="3,1,4,1,5,9,2,6", offset=5):
    return _wheel(t, order, offset, -1)


def jw_a(ct, lang="en"):
    """The disc alphabets are public, so test each disc and offset per column."""
    t = letters(ct)
    discs = _discs()
    letter = np.log(model(lang)["letter"] + 1e-6)
    best = (-1e18, None, None)
    for offset in range(1, 26):
        for p in (6, 8, 10, 12, 16, 20, 25):
            order, total = [], 0.0
            for col in range(p):
                sc = [sum(letter[ord(d[(d.index(c) - offset) % 26]) - 65] for c in t[col::p]) for d in discs]
                j = int(np.argmax(sc))
                order.append(j)
                total += sc[j]
            total -= 3.0 * p
            if total > best[0]:
                best = (total, ",".join(map(str, order)), offset)
    return X.result(jw_d(ct, best[1], best[2]), {"order": best[1], "offset": best[2]}, "per-column disc and offset fit", lang)


add(id="jefferson", name="Jefferson wheel", family="Machines", era="Thomas Jefferson, c. 1795; M-94 US Army, 1922", summary="A stack of lettered discs; send any other row.",
    how="Discs are arranged in a secret order, the message is dialled along one row, and another row is sent. Here the disc alphabets are fixed and public, as in a captured device.",
    weakness="If the discs are known, each position has only a few candidates, and the period can be tested per column.", encrypt=jw_e, decrypt=jw_d, key={"order": "3,1,4,1,5,9,2,6", "offset": 5}, example="Wheels within wheels",
    params=[Param("order", "Disc order, comma separated"), Param("offset", "Row offset", "int")], attack=jw_a, attack_name="Per-column disc and offset fit",
    keygen=lambda r: {"order": ",".join(str(r.randint(0, 25)) for _ in range(8)), "offset": r.randint(1, 25)})


LORENZ_SIZES = [41, 31, 29, 26, 23, 43, 47, 51, 53, 59]


def _lorenz_wheels(seed=1941):
    r = random.Random(seed)
    return [[r.randint(0, 1) for _ in range(s)] for s in LORENZ_SIZES]


def _lorenz_stream(n, start):
    w, out = _lorenz_wheels(), []
    start = [int(x) for x in str(start).split(",")]
    start = (start + [0] * 10)[:10]
    for i in range(n):
        v = 0
        for b in range(5):
            v |= (w[b][(start[b] + i) % LORENZ_SIZES[b]] ^ w[b + 5][(start[b + 5] + i // 2) % LORENZ_SIZES[b + 5]]) << b
        out.append(v)
    return out


def lz(t, start="1,2,3,4,5,6,7,8,9,10"):
    data = [A.index(c) for c in letters(t)]
    return " ".join(f"{a ^ b:02d}" for a, b in zip(data, _lorenz_stream(len(data), start)))


def lz_d(t, start="1,2,3,4,5,6,7,8,9,10"):
    data = [int(x) for x in t.split()]
    return "".join(A[(a ^ b) % 26] for a, b in zip(data, _lorenz_stream(len(data), start)))


def lz_demo(seed):
    a, b = "ATTACKTHEBRIDGEATDAWNWITHTANKS", "RETREATTOTHERIVERBEFORENIGHTXX"
    ca, cb = [int(x) for x in lz(a).split()], [int(x) for x in lz(b).split()]
    depth = [x ^ y for x, y in zip(ca, cb)]
    rec = "".join(A[(d ^ A.index(c)) % 26] for d, c in zip(depth, a))
    return {"kind": "modern", "title": "Depth: two messages sent on one wheel setting", "steps": [
        "In August 1941 a Lorenz operator resent a long message at the same setting. British analyst John Tiltman used that depth to recover the key stream.",
        f"Message 1 ciphertext: {' '.join(map(str, ca[:10]))} ...", f"XOR of both ciphertexts cancels the key: {' '.join(map(str, depth[:10]))} ...",
        f"A correct guess of message 1 ('{a[:12]}...') exposes message 2."], "recovered": rec, "truth": b, "success": rec == b}


add(id="lorenz", name="Lorenz SZ (teaching model)", family="Machines", era="Germany, WWII; broken at Bletchley Park", summary="A simplified 5-bit stream cipher from ten wheels.",
    how="Real Lorenz had twelve wheels with irregular motion and worked in Baudot. This model keeps the essential idea: five bits per character, each XORed with two wheel streams. Wheel patterns are fixed and the start positions are the key.",
    weakness="Two messages on the same setting cancel the key. Tiltman and Bill Tutte used this to deduce the whole machine without ever seeing one. Colossus was built to automate the attack.",
    encrypt=lz, decrypt=lz_d, key={"start": "1,2,3,4,5,6,7,8,9,10"}, example="Geheimschreiber", params=[Param("start", "Ten wheel starts")], demo_attack=lz_demo)


def _book_initials():
    raw = (ROOT / "data/sources/declaration.txt").read_text(errors="ignore")
    i = raw.lower().index("when in the course of human events")
    j = raw.find("*** END", i)
    import re
    return [w[0].upper() for w in re.findall(r"[A-Za-z'’]+", raw[i:j].replace("-", " "))]


def book_e(t, offset=0):
    init, off = _book_initials(), int(offset)
    pos: dict = {}
    for i, c in enumerate(init):
        if i >= off:
            pos.setdefault(c, []).append(i - off + 1)
    r = random.Random(0)
    fallback = {"X": "S", "Z": "S", "Q": "C", "K": "C", "J": "I"}
    return " ".join(str(r.choice(pos.get(c) or pos.get(fallback.get(c, "S")) or pos["T"])) for c in letters(t))


def book_d(t, offset=0):
    init, off = _book_initials(), int(offset)
    return "".join(init[int(n) - 1 + off] for n in t.split() if int(n) - 1 + off < len(init))


def book_a(ct, lang="en"):
    nums = np.array([int(x) for x in ct.split()], dtype=np.int64)
    ini = to_ints("".join(_book_initials()))
    s = K.book_offset_scan(nums, ini, model(lang)["table"], 1200)
    return X.result(book_d(ct, int(np.argmax(s))), {"offset": int(np.argmax(s))}, "slid the numbers along the candidate key text", lang)


add(id="book", name="Book cipher", family="Book and homophonic", era="Beale papers, 1885; Benedict Arnold, 1780", summary="Numbers point to words in a shared text; use their first letters.",
    how="Each plaintext letter is replaced by the number of any word in a key text starting with that letter. Beale 2 used the Declaration of Independence, and so does this demo. The offset models a different starting point in the text.",
    weakness="With the right text the message is immediate. Without it the numbers carry almost no statistics, which is why Beale 1 and 3 remain open.",
    encrypt=book_e, decrypt=book_d, key={"offset": 0}, example="Hide it near the mountain", params=[Param("offset", "Word offset into the text", "int")], attack=book_a, attack_name="Slide numbers along a candidate key text", keygen=lambda r: {"offset": r.randint(0, 400)})


def _homophones(seed, total=48):
    freq, r = model("en")["letter"], random.Random(int(seed))
    counts = [max(1, round(float(f) * total)) for f in freq]
    nums = r.sample(range(10, 99), sum(counts))
    table, p = {}, 0
    for i, c in enumerate(A):
        table[c] = nums[p:p + counts[i]]
        p += counts[i]
    return table


def hom_e(t, seed=7):
    tb, r = _homophones(seed), random.Random(int(seed) + 1)
    return " ".join(str(r.choice(tb[c])) for c in letters(t))


def hom_d(t, seed=7):
    inv = {n: c for c, v in _homophones(seed).items() for n in v}
    return "".join(inv[int(x)] for x in t.split())


add(id="homophonic", name="Homophonic substitution", family="Book and homophonic", era="Italy, 15th century; Copiale; Z408", summary="Several symbols for each common letter, flattening frequencies.",
    how="E might have six symbols and Z only one, so each symbol appears about equally often. Here a seed chooses 48 two-digit homophones.",
    weakness="Letter contact patterns survive. Solvers such as AZdecrypt anneal symbol assignments, and the Zodiac's Z408 fell this way. It does need enough text relative to the number of symbols.",
    encrypt=hom_e, decrypt=hom_d, key={"seed": 7}, example="Many symbols for each letter", params=[Param("seed", "Table seed", "int")],
    attack=lambda ct, lang="en": X.solve_symbols(ct.split(), lang, homophonic=True), attack_name="Simulated annealing over homophone assignments", keygen=lambda r: {"seed": r.randint(1, 10**6)})
