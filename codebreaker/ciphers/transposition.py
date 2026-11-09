"""Ciphers that rearrange letters without changing them."""
import itertools
import random as _random

import numpy as np

from .. import kernels as K
from ..attacks import classical as X
from ..languages import keywords, model
from ..text import letters, to_ints, to_text
from .base import Param, add, dict_word
from .columns import col_decrypt, col_encrypt, order

FAM = "Transposition"
P_WORD = Param("keyword", "Keyword")


def _rail_pattern(n, rails):
    period = max(2 * (rails - 1), 1)
    return [min(i % period, period - i % period) for i in range(n)]


def rail_e(t, rails=3):
    t, pat = letters(t), _rail_pattern(len(letters(t)), int(rails))
    return "".join(t[i] for r in range(int(rails)) for i in range(len(t)) if pat[i] == r)


def rail_d(t, rails=3):
    t, pat = letters(t), _rail_pattern(len(letters(t)), int(rails))
    idx = [i for r in range(int(rails)) for i in range(len(t)) if pat[i] == r]
    out = [""] * len(t)
    for i, c in zip(idx, t):
        out[i] = c
    return "".join(out)


add(id="railfence", name="Rail fence", family=FAM, era="Traditional; American Civil War", summary="Write in a zigzag across rails, then read row by row.",
    how="Letters bounce down and up the rails. Reading each rail in turn gives the ciphertext.", weakness="The key is the number of rails, which is at most the length of the message.",
    encrypt=rail_e, decrypt=rail_d, key={"rails": 3}, example="We are discovered flee at once", params=[Param("rails", "Rails", "int")],
    attack=lambda ct, lang="en": X.keyspace(lambda rails: rail_d(ct, rails), ({"rails": r} for r in range(2, min(40, len(letters(ct))))), lang, "tried every rail count"),
    attack_name="Try every rail count", keygen=lambda r: {"rails": r.randint(2, 12)})


def scy_e(t, turns=4):
    t, k = letters(t), int(turns)
    return "".join(t[i::k] for i in range(k))


def scy_d(t, turns=4):
    t, k = letters(t), int(turns)
    return col_decrypt(t, "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:k])


add(id="scytale", name="Scytale", family=FAM, era="Sparta, c. 5th century BC", summary="Wrap a strip around a rod and write along it.",
    how="Unwound, the strip shows scrambled letters. Only a rod of the same thickness realigns them. The rod's circumference is the key.", weakness="Only a handful of rod sizes are possible.",
    encrypt=scy_e, decrypt=scy_d, key={"turns": 4}, example="Send more spears to Sparta", params=[Param("turns", "Letters per turn", "int")],
    attack=lambda ct, lang="en": X.keyspace(lambda turns: scy_d(ct, turns), ({"turns": k} for k in range(2, 26)), lang, "tried every rod size"),
    attack_name="Try every rod size", keygen=lambda r: {"turns": r.randint(2, 20)})


def col_e(t, keyword="ZEBRAS"):
    return col_encrypt(letters(t), keyword)


def col_d(t, keyword="ZEBRAS"):
    return col_decrypt(letters(t), keyword)


add(id="columnar", name="Columnar transposition", family=FAM, era="Used widely into WWII", summary="Write in rows, then read columns in keyword order.",
    how="The alphabetical order of the keyword's letters sets the column read order. An uneven last row makes it harder.",
    weakness="Reassembling columns with digraph or quadgram scoring reveals the order, and no keyword dictionary is needed.",
    encrypt=col_e, decrypt=col_d, key={"keyword": "ZEBRAS"}, example="Columns scatter neighbours", params=[P_WORD], attack=X.columnar_search, attack_name="Hill climb on column order",
    keygen=lambda r: {"keyword": dict_word(r)[:10]})


def dbl_e(t, key1="ZEBRAS", key2="STRIPE"):
    return col_encrypt(col_encrypt(letters(t), key1), key2)


def dbl_d(t, key1="ZEBRAS", key2="STRIPE"):
    return col_decrypt(col_decrypt(letters(t), key2), key1)


def dbl_a(ct, lang="en"):
    words = keywords(lang, 160, 4)
    return X.keyspace(lambda key1, key2: dbl_d(ct, key1, key2), ({"key1": a, "key2": b} for a in words for b in words), lang, "keyword-pair dictionary")


add(id="double", name="Double columnar", family=FAM, era="WWI and WWII field cipher", summary="Columnar transposition applied twice.",
    how="It was considered secure in the field, and was used by agents and resistance groups into WWII.", weakness="Word keys are guessable, and two messages of equal length with the same keys can be solved by anagramming together.",
    encrypt=dbl_e, decrypt=dbl_d, key={"key1": "ZEBRAS", "key2": "STRIPE"}, example="Twice scattered still leaks", params=[Param("key1", "First keyword"), Param("key2", "Second keyword")], attack=dbl_a, attack_name="Keyword-pair dictionary",
    keygen=lambda r: {"key1": r.choice(keywords("en", 160, 4)), "key2": r.choice(keywords("en", 160, 4))})


def _spiral(rows, cols):
    top, bot, left, right, path = 0, rows - 1, 0, cols - 1, []
    while top <= bot and left <= right:
        path += [top * cols + c for c in range(left, right + 1)]
        path += [r * cols + right for r in range(top + 1, bot + 1)]
        if top < bot:
            path += [bot * cols + c for c in range(right - 1, left - 1, -1)]
        if left < right:
            path += [r * cols + left for r in range(bot - 1, top, -1)]
        top, bot, left, right = top + 1, bot - 1, left + 1, right - 1
    return path


def _fill(t, cols):
    t = letters(t)
    return t + "X" * ((-len(t)) % int(cols))


def route_e(t, cols=6):
    t, c = _fill(t, cols), int(cols)
    return "".join(t[i] for i in _spiral(len(t) // c, c))


def route_d(t, cols=6):
    t, c = letters(t), int(cols)
    out = [""] * len(t)
    for ch, i in zip(t, _spiral(len(t) // c, c)):
        out[i] = ch
    return "".join(out)


def route_a(ct, lang="en"):
    n = len(letters(ct))
    return X.keyspace(lambda cols: route_d(ct, cols), ({"cols": c} for c in range(2, n) if n % c == 0), lang, "tried every grid that fits")


add(id="route", name="Route (spiral)", family=FAM, era="Union Army, American Civil War", summary="Fill a grid by rows and read it along a spiral path.",
    how="The grid shape and the route are the key. Union telegraph ciphers combined routes with code words.", weakness="Grid shapes are limited by the factors of the message length.",
    encrypt=route_e, decrypt=route_d, key={"cols": 6}, example="Along a winding path we go", params=[Param("cols", "Columns", "int")], attack=route_a, attack_name="Try every grid that fits", keygen=lambda r: {"cols": r.randint(3, 15)})


def _mysz_rank(key):
    k = letters(key)
    u = sorted(set(k))
    return [u.index(c) for c in k]


def my_e(t, keyword="BANANA"):
    t, rank = letters(t), _mysz_rank(keyword)
    k, out = len(rank), []
    for r in sorted(set(rank)):
        cols = [c for c in range(k) if rank[c] == r]
        for row in range(0, len(t), k):
            out += [t[row + c] for c in cols if row + c < len(t)]
    return "".join(out)


def my_d(t, keyword="BANANA"):
    t, rank = letters(t), _mysz_rank(keyword)
    k, pos, out = len(rank), 0, [""] * len(t)
    for r in sorted(set(rank)):
        cols = [c for c in range(k) if rank[c] == r]
        for row in range(0, len(t), k):
            for c in cols:
                if row + c < len(t):
                    out[row + c] = t[pos]
                    pos += 1
    return "".join(out)


add(id="myszkowski", name="Myszkowski", family=FAM, era="Emile Myszkowski, 1902", summary="Columnar, with repeated key letters read across together.",
    how="Columns sharing a key letter are read row by row together, which complicates column reassembly.", weakness="Word keys are guessable, and neighbouring statistics remain partly intact.",
    encrypt=my_e, decrypt=my_d, key={"keyword": "BANANA"}, example="Repeated letters read together", params=[P_WORD],
    attack=lambda ct, lang="en": X.keyspace(lambda keyword: my_d(ct, keyword), X.word_keys("keyword", lang), lang, "keyword dictionary"), attack_name="Keyword dictionary", keygen=lambda r: {"keyword": dict_word(r)})


def _amsco_cells(n, key):
    k = len(order(key))
    cells, used, size, row = [], 0, 1, 0
    while used < n:
        for c in range(k):
            if used >= n:
                break
            take = min(size, n - used)
            cells.append((row, c, used, take))
            used += take
            size = 3 - size
        row += 1
        size = 1 if row % 2 == 0 else 2
    return cells


def am_e(t, keyword="ZEBRAS"):
    t, cells = letters(t), _amsco_cells(len(letters(t)), keyword)
    return "".join(t[s:s + z] for col in order(keyword) for r, c, s, z in cells if c == col)


def am_d(t, keyword="ZEBRAS"):
    t, cells = letters(t), _amsco_cells(len(letters(t)), keyword)
    out, pos = [""] * len(t), 0
    for col in order(keyword):
        for r, c, s, z in cells:
            if c == col:
                out[s:s + z] = t[pos:pos + z]
                pos += z
    return "".join(out)


add(id="amsco", name="AMSCO", family=FAM, era="A. M. Scott, 20th century", summary="Columnar transposition with cells alternating one and two letters.",
    how="Keeping some letter pairs together while splitting others defeats simple digram reassembly.", weakness="Word keys are guessable, and search over patterns works.", encrypt=am_e, decrypt=am_d, key={"keyword": "ZEBRAS"}, example="Alternating cells of letters", params=[P_WORD],
    attack=lambda ct, lang="en": X.keyspace(lambda keyword: am_d(ct, keyword), X.word_keys("keyword", lang), lang, "keyword dictionary"), attack_name="Keyword dictionary", keygen=lambda r: {"keyword": dict_word(r)})


def _grille_holes(key):
    """Key: nine digits 0-3, one per orbit of a 6x6 grid, giving the hole's rotation."""
    n, holes, orbit = 6, [], 0
    for r in range(3):
        for c in range(3):
            p = (r, c)
            for _ in range(int(key[orbit])):
                p = (p[1], n - 1 - p[0])
            holes.append(p)
            orbit += 1
    return holes


def _rot(p):
    return (p[1], 5 - p[0])


def _grille_order(key):
    holes, seq = _grille_holes(key), []
    for _ in range(4):
        seq += sorted(p[0] * 6 + p[1] for p in holes)
        holes = [_rot(p) for p in holes]
    return seq


def gr_e(t, key="012301230"):
    t, o, out = letters(t), _grille_order(key), []
    t += "X" * ((-len(t)) % 36)
    for b in range(0, len(t), 36):
        grid = [""] * 36
        for i, ch in zip(o, t[b:b + 36]):
            grid[i] = ch
        out += grid
    return "".join(out)


def gr_d(t, key="012301230"):
    t, o = letters(t), _grille_order(key)
    return "".join(t[b + i] for b in range(0, len(t), 36) for i in o)


def gr_a(ct, lang="en"):
    r, best, best_k = _random.Random(1), -1e18, "0" * 9
    from ..languages import score
    for _ in range(25):
        k = [r.randint(0, 3) for _ in range(9)]
        cur = score(gr_d(ct, "".join(map(str, k))), lang)
        improved = True
        while improved:
            improved = False
            for i in range(9):
                for v in range(4):
                    old, k[i] = k[i], v
                    s = score(gr_d(ct, "".join(map(str, k))), lang)
                    if s > cur + 1e-9:
                        cur, improved = s, True
                    else:
                        k[i] = old
        if cur > best:
            best, best_k = cur, "".join(map(str, k))
    return X.result(gr_d(ct, best_k), {"key": best_k}, "hill climb over 4^9 grilles", lang)


add(id="grille", name="Turning grille", family=FAM, era="Fleissner, 1881; idea from Cardano", summary="A card with holes, rotated four times over a grid.",
    how="Write through the holes, rotate 90 degrees, and repeat. The nine digits choose one of four positions for each hole.", weakness="Only 4^9 grilles exist at this size, and partial grilles reveal readable fragments.",
    encrypt=gr_e, decrypt=gr_d, key={"key": "012301230"}, example="Holes in a rotating card reveal the words", params=[Param("key", "Nine digits, 0 to 3")], attack=gr_a, attack_name="Hill climb over the 4^9 grilles",
    keygen=lambda r: {"key": "".join(str(r.randint(0, 3)) for _ in range(9))})
