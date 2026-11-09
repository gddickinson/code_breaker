"""Ciphers acting on letter pairs or on fractionated coordinates."""
import numpy as np
from sympy import Matrix

from .. import kernels as K
from ..attacks import classical as X
from ..languages import keywords, model
from ..text import A, keyed_alphabet, letters, to_ints, to_text
from .base import Param, add, dict_word
from .columns import col_decrypt, col_encrypt
from .monoalphabetic import square

FAM, FRAC = "Polygraphic", "Fractionating"
P_WORD = Param("keyword", "Keyword")


def _digraphs(t):
    t, out, i = letters(t).replace("J", "I"), [], 0
    while i < len(t):
        a = t[i]
        b = t[i + 1] if i + 1 < len(t) else "X"
        if a == b:
            out.append((a, "X" if a != "X" else "Q"))
            i += 1
        else:
            out.append((a, b))
            i += 2
    return out


def _playfair(pairs, sq, d):
    out = []
    for a, b in pairs:
        p, q = sq.index(a), sq.index(b)
        r1, c1, r2, c2 = p // 5, p % 5, q // 5, q % 5
        if r1 == r2:
            c1, c2 = (c1 + d) % 5, (c2 + d) % 5
        elif c1 == c2:
            r1, r2 = (r1 + d) % 5, (r2 + d) % 5
        else:
            c1, c2 = c2, c1
        out += [sq[r1 * 5 + c1], sq[r2 * 5 + c2]]
    return "".join(out)


def pf_e(t, keyword="PLAYFAIR"):
    return _playfair(_digraphs(t), square(keyword), 1)


def pf_d(t, keyword="PLAYFAIR"):
    x = letters(t)
    return _playfair(list(zip(x[::2], x[1::2])), square(keyword), 4)


add(id="playfair", name="Playfair", family=FAM, era="Wheatstone, 1854; used in the Boer War and WWI", summary="Encrypt letter pairs using rectangles in a 5x5 square.",
    how="Same row: move right. Same column: move down. Otherwise take the opposite corners of the rectangle. Doubled letters get an X between them.",
    weakness="Digraph statistics survive, and there are only 600 common digraphs. Annealing the square with quadgram scoring breaks it.",
    encrypt=pf_e, decrypt=pf_d, key={"keyword": "PLAYFAIR"}, example="Hide the gold under the old stump", params=[P_WORD],
    attack=X.playfair, attack_name="Simulated annealing on the square", keygen=lambda r: {"keyword": dict_word(r)})


def _cell(sq, c):
    return sq.index(c) // 5, sq.index(c) % 5


def _pad(t):
    t = letters(t).replace("J", "I")
    return t + "X" * (len(t) % 2)


def ts_e(t, key1="EXAMPLE", key2="KEYWORD"):
    s1, s2, t, out = square(key1), square(key2), _pad(t), []
    for a, b in zip(t[::2], t[1::2]):
        (r1, c1), (r2, c2) = _cell(s1, a), _cell(s2, b)
        out += [s2[r1 * 5 + c2], s1[r2 * 5 + c1]]
    return "".join(out)


def ts_d(t, key1="EXAMPLE", key2="KEYWORD"):
    s1, s2, t, out = square(key1), square(key2), _pad(t), []
    for x, y in zip(t[::2], t[1::2]):
        (r1, c2), (r2, c1) = _cell(s2, x), _cell(s1, y)
        out += [s1[r1 * 5 + c1], s2[r2 * 5 + c2]]
    return "".join(out)


def two_words(n=70):
    return keywords("en", n, 4)


def ts_a(ct, lang="en"):
    w = two_words()
    return X.keyspace(lambda key1, key2: ts_d(ct, key1, key2), ({"key1": a, "key2": b} for a in w for b in w), lang, "keyword-pair dictionary")


TWO = lambda r: {"key1": r.choice(two_words()), "key2": r.choice(two_words())}
P_TWO = [Param("key1", "Keyword 1"), Param("key2", "Keyword 2")]
add(id="twosquare", name="Two-square", family=FAM, era="Delastelle tradition, 19th century", summary="Two keyed squares, encrypting pairs by rectangle.",
    how="The first letter is found in square 1 and the second in square 2. Output letters come from the opposite corners.", weakness="Digraph statistics survive, and keys from ordinary words are guessable.",
    encrypt=ts_e, decrypt=ts_d, key={"key1": "EXAMPLE", "key2": "KEYWORD"}, example="Two squares hide pairs", params=P_TWO, attack=ts_a, attack_name="Keyword-pair dictionary", keygen=TWO)

STD = A.replace("J", "")


def fs_e(t, key1="EXAMPLE", key2="KEYWORD"):
    s1, s2, t, out = square(key1), square(key2), _pad(t), []
    for a, b in zip(t[::2], t[1::2]):
        (r1, c1), (r2, c2) = _cell(STD, a), _cell(STD, b)
        out += [s1[r1 * 5 + c2], s2[r2 * 5 + c1]]
    return "".join(out)


def fs_d(t, key1="EXAMPLE", key2="KEYWORD"):
    s1, s2, t, out = square(key1), square(key2), _pad(t), []
    for x, y in zip(t[::2], t[1::2]):
        (r1, c2), (r2, c1) = _cell(s1, x), _cell(s2, y)
        out += [STD[r1 * 5 + c1], STD[r2 * 5 + c2]]
    return "".join(out)


def fs_a(ct, lang="en"):
    w = two_words()
    return X.keyspace(lambda key1, key2: fs_d(ct, key1, key2), ({"key1": a, "key2": b} for a in w for b in w), lang, "keyword-pair dictionary")


add(id="foursquare", name="Four-square", family=FAM, era="Felix Delastelle, 1902", summary="Four 5x5 squares: two plain and two keyed.",
    how="Plaintext pairs are located in the plain squares, and the opposite corners are read from the keyed squares.", weakness="It stays a digraph substitution with 600 common pairs, and word keys are guessable.",
    encrypt=fs_e, decrypt=fs_d, key={"key1": "EXAMPLE", "key2": "KEYWORD"}, example="Delastelle liked squares", params=P_TWO, attack=fs_a, attack_name="Keyword-pair dictionary", keygen=TWO)


def _matrix(key):
    v = [int(x) for x in str(key).replace(" ", "").split(",")]
    n = int(len(v) ** 0.5)
    if n * n != len(v):
        raise ValueError("Hill key must be a square matrix, e.g. 3,3,2,5")
    return np.array(v).reshape(n, n)


def _hill(t, m):
    x, n = to_ints(t), m.shape[0]
    x = np.concatenate((x, np.full((-len(x)) % n, 23)))
    return to_text((m @ x.reshape(-1, n).T).T.flatten() % 26)


def hill_e(t, key="3,3,2,5"):
    return _hill(t, _matrix(key))


def hill_d(t, key="3,3,2,5"):
    return _hill(t, np.array(Matrix(_matrix(key).tolist()).inv_mod(26).tolist(), dtype=int))


def hill_gen(r):
    while True:
        a, b, c, d = [r.randint(0, 25) for _ in range(4)]
        det = (a * d - b * c) % 26
        if det % 2 and det != 13:
            return {"key": f"{a},{b},{c},{d}"}


add(id="hill", name="Hill", family=FAM, era="Lester Hill, 1929", summary="Linear algebra: multiply letter blocks by a key matrix mod 26.",
    how="Enter the matrix row by row. The determinant must be coprime to 26. It was the first practical polygraphic system to work on more than three letters at once.",
    weakness="It is completely linear, so a few known plaintext blocks solve the key. A 2x2 key has only about 157,000 candidates.",
    encrypt=hill_e, decrypt=hill_d, key={"key": "3,3,2,5"}, example="Linear means breakable", params=[Param("key", "Matrix, comma separated")],
    attack=X.hill2, attack_name="Every invertible 2x2 matrix (2x2 keys only)", keygen=hill_gen)


def _period_blocks(s, period):
    p = int(period) or len(s)
    return [s[i:i + p] for i in range(0, len(s), p)]


def bif_e(t, keyword="BIFID", period=5):
    s, out = square(keyword), []
    for b in _period_blocks(letters(t).replace("J", "I"), period):
        c = [_cell(s, x) for x in b]
        co = [r for r, _ in c] + [q for _, q in c]
        out += [s[co[i] * 5 + co[i + 1]] for i in range(0, len(co), 2)]
    return "".join(out)


def bif_d(t, keyword="BIFID", period=5):
    s, out = square(keyword), []
    for b in _period_blocks(letters(t).replace("J", "I"), period):
        co = [v for x in b for v in _cell(s, x)]
        h = len(co) // 2
        out += [s[co[i] * 5 + co[i + h]] for i in range(h)]
    return "".join(out)


P_FR = [P_WORD, Param("period", "Period (0 = whole message)", "int")]


def bif_a(ct, lang="en"):
    keys = ({"keyword": w, "period": p} for w in keywords(lang, 2500, 4) for p in (5, 7, 0))
    return X.keyspace(lambda keyword, period: bif_d(ct, keyword, period), keys, lang, "keyword dictionary across common periods")


add(id="bifid", name="Bifid", family=FRAC, era="Delastelle, 1901", summary="Split letters into coordinates, mix them, and recombine.",
    how="Write the row and column numbers of each letter on two lines, then read them across in pairs. One ciphertext letter now depends on two plaintext letters.",
    weakness="The period shows up statistically, and word keys are guessable. Annealing the square also works on longer texts.",
    encrypt=bif_e, decrypt=bif_d, key={"keyword": "BIFID", "period": 5}, example="Fractionation spreads letters", params=P_FR, attack=bif_a, attack_name="Keyword dictionary across periods",
    keygen=lambda r: {"keyword": dict_word(r), "period": r.choice([5, 7])})

T27 = A + "+"


def _cube(keyword):
    return keyed_alphabet(keyword, T27)


def tri_e(t, keyword="TRIFID", period=5):
    c, out = _cube(keyword), []
    for b in _period_blocks(letters(t), period):
        co = [[c.index(x) // 9 for x in b], [c.index(x) // 3 % 3 for x in b], [c.index(x) % 3 for x in b]]
        f = co[0] + co[1] + co[2]
        out += [c[f[i] * 9 + f[i + 1] * 3 + f[i + 2]] for i in range(0, len(f), 3)]
    return "".join(out)


def tri_d(t, keyword="TRIFID", period=5):
    c, out = _cube(keyword), []
    s = "".join(x for x in t.upper() if x in T27)
    for b in _period_blocks(s, period):
        f = [v for x in b for v in (c.index(x) // 9, c.index(x) // 3 % 3, c.index(x) % 3)]
        h = len(b)
        out += [c[f[i] * 9 + f[i + h] * 3 + f[i + 2 * h]] for i in range(h)]
    return "".join(out)


def tri_a(ct, lang="en"):
    keys = ({"keyword": w, "period": p} for w in keywords(lang, 2500, 4) for p in (5, 7))
    return X.keyspace(lambda keyword, period: tri_d(ct, keyword, period), keys, lang, "keyword dictionary across common periods")


add(id="trifid", name="Trifid", family=FRAC, era="Delastelle, 1902", summary="Bifid in three dimensions: a 3x3x3 cube.",
    how="Each letter becomes three coordinates, spreading its influence across three ciphertext letters. Claude Shannon later named this idea diffusion.",
    weakness="Period analysis and guessable keys.", encrypt=tri_e, decrypt=tri_d, key={"keyword": "TRIFID", "period": 5}, example="Three dimensions of letters", params=P_FR, attack=tri_a, attack_name="Keyword dictionary across periods",
    keygen=lambda r: {"keyword": dict_word(r), "period": r.choice([5, 7])})


def _adfg(labels, alphabet, n):
    def enc(t, keyword="CIPHER", transposition="GERMAN"):
        s = keyed_alphabet(keyword, alphabet)
        src = letters(t).replace("J", "I") if n == 5 else "".join(c for c in t.upper() if c in alphabet)
        return col_encrypt("".join(labels[s.index(c) // n] + labels[s.index(c) % n] for c in src), transposition)

    def dec(t, keyword="CIPHER", transposition="GERMAN"):
        s = keyed_alphabet(keyword, alphabet)
        f = col_decrypt("".join(c for c in t.upper() if c in labels), transposition)
        return "".join(s[labels.index(f[i]) * n + labels.index(f[i + 1])] for i in range(0, len(f) - 1, 2))

    def attack(ct, lang="en"):
        best = (-1.0, None)
        for w in keywords(lang, 2500, 4):
            f = col_decrypt(ct, w)
            c = np.unique([f[i:i + 2] for i in range(0, len(f) - 1, 2)], return_counts=True)[1]
            v = float((c * (c - 1)).sum())
            if v > best[0]:
                best = (v, w)
        w = best[1]
        r = X.solve_symbols(X.pairs(col_decrypt(ct, w)), lang)
        r["key"] = {"transposition": w, "pairs": r["key"]}
        r["method"] = "pair-frequency test on transposition keys, then anneal the substitution"
        return r

    return enc, dec, attack


e5, d5, a5 = _adfg("ADFGX", STD, 5)
P_AD = [Param("keyword", "Square keyword"), Param("transposition", "Transposition keyword")]
GEN = lambda r: {"keyword": dict_word(r), "transposition": dict_word(r)}
add(id="adfgx", name="ADFGX", family=FRAC, era="Fritz Nebel, Germany, March 1918", summary="Fractionate into five Morse-distinct letters, then transpose.",
    how="A keyed square gives each letter two signal letters, then a keyed columnar transposition scatters them. German forces used it during the 1918 offensives.",
    weakness="Georges Painvin broke it by hand. The right transposition makes pair frequencies spike, after which it is a plain substitution.",
    encrypt=e5, decrypt=d5, key={"keyword": "CIPHER", "transposition": "GERMAN"}, example="Attack at the Somme", params=P_AD, attack=a5, attack_name="Pair-frequency test, then anneal the substitution", keygen=GEN)
e6, d6, a6 = _adfg("ADFGVX", A + "0123456789", 6)
add(id="adfgvx", name="ADFGVX", family=FRAC, era="Germany, June 1918", summary="ADFGX enlarged to 6x6, adding digits.",
    how="A sixth signal letter allows all 26 letters and ten digits.", weakness="Same as ADFGX. Painvin's break is credited with helping to halt the June 1918 German advance.",
    encrypt=e6, decrypt=d6, key={"keyword": "CIPHER", "transposition": "GERMAN"}, example="Munition stock", params=P_AD, attack=a6, attack_name="Pair-frequency test, then anneal the substitution", keygen=GEN)


def nih_e(t, keyword="ZEBRAS", key="RUSSIAN"):
    s, k = square(keyword), letters(key).replace("J", "I")
    return " ".join(str((s.index(c) // 5 + 1) * 10 + s.index(c) % 5 + 1 + (s.index(k[i % len(k)]) // 5 + 1) * 10 + s.index(k[i % len(k)]) % 5 + 1)
                    for i, c in enumerate(letters(t).replace("J", "I")))


def nih_d(t, keyword="ZEBRAS", key="RUSSIAN"):
    s, k, out = square(keyword), letters(key).replace("J", "I"), []
    for i, n in enumerate(t.split()):
        v = int(n) - ((s.index(k[i % len(k)]) // 5 + 1) * 10 + s.index(k[i % len(k)]) % 5 + 1)
        out.append(s[(v // 10 - 1) * 5 + v % 10 - 1])
    return "".join(out)


def nih_a(ct, lang="en"):
    """Correct additive key leaves every pair with digits 1-5: a very strong filter."""
    nums = np.array([int(x) for x in ct.split()])
    s = square("")
    best = (-1, None, None)
    for w in keywords(lang, 2500, 3):
        k = np.array([(s.index(c) // 5 + 1) * 10 + s.index(c) % 5 + 1 for c in letters(w).replace("J", "I")])
        for off in [0]:
            v = nums - np.resize(k, len(nums))
            ok = ((v // 10 >= 1) & (v // 10 <= 5) & (v % 10 >= 1) & (v % 10 <= 5)).mean()
            if ok > best[0]:
                best = (ok, w, v)
    r = X.solve_symbols([str(x) for x in best[2]], lang)
    r["key"] = {"additive_key_in_plain_square": best[1], "valid_fraction": round(float(best[0]), 3)}
    return r


add(id="nihilist", name="Nihilist", family=FRAC, era="Russian Nihilists, 1880s", summary="Add a repeating key's Polybius numbers to the message's.",
    how="Both message and key become two-digit Polybius numbers, which are added without carrying modulo 100.",
    weakness="Additive structure leaks: sums reveal digit limits, and a valid key leaves only digits 1 to 5. Here the demo assumes a square that shares structure with the plain one.",
    encrypt=nih_e, decrypt=nih_d, key={"keyword": "", "key": "RUSSIAN"}, example="Dynamite in the cellar", params=[Param("keyword", "Square keyword"), Param("key", "Additive keyword")],
    attack=nih_a, attack_name="Digit-range filter on additive keys, then anneal", keygen=lambda r: {"keyword": "", "key": dict_word(r)})


def _board(keyword):
    s = keyed_alphabet(keyword)
    top, row2, row6 = s[:8], s[8:17], s[17:]
    table, n = {}, 0
    cols = [c for c in "0134578 9".replace(" ", "")]
    for i, c in enumerate(top):
        table[c] = "01345789"[i]
    for i, c in enumerate(row2):
        table[c] = "2" + "0123456789"[i]
    for i, c in enumerate(row6):
        table[c] = "6" + "0123456789"[i]
    return table


def sc_e(t, keyword="ESTONIA"):
    b = _board(keyword)
    return "".join(b[c] for c in letters(t))


def sc_d(t, keyword="ESTONIA"):
    inv = {v: k for k, v in _board(keyword).items()}
    d, i, out = "".join(c for c in t if c.isdigit()), 0, []
    while i < len(d):
        if d[i] in "26":
            out.append(inv.get(d[i:i + 2], ""))
            i += 2
        else:
            out.append(inv.get(d[i], ""))
            i += 1
    return "".join(out)


def sc_a(ct, lang="en"):
    return X.keyspace(lambda keyword: sc_d(ct, keyword), X.word_keys("keyword", lang), lang, "keyword dictionary")


add(id="checkerboard", name="Straddling checkerboard", family=FRAC, era="Soviet spies, mid-20th century", summary="Common letters get one digit and rare ones two.",
    how="Eight letters take single digits. Two digits (here 2 and 6) introduce two-digit codes. This compresses the message and blurs digit boundaries. It formed part of the VIC cipher.",
    weakness="On its own it is a variable-length substitution. Real use superencrypted it.", encrypt=sc_e, decrypt=sc_d, key={"keyword": "ESTONIA"}, example="Meet at the station", params=[P_WORD], attack=sc_a, attack_name="Keyword dictionary", keygen=lambda r: {"keyword": dict_word(r)})
