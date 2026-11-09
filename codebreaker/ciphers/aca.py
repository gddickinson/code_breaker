"""More classical types from the American Cryptogram Association tradition, plus the M-209."""
import random

import numpy as np

from ..attacks import classical as X
from ..languages import keywords
from ..text import A, keyed_alphabet, letters, to_ints, to_text
from .base import Param, add, dict_word
from .columns import order
from .monoalphabetic import MORSE, UNMORSE

P2 = [Param("alphabet", "Alphabet keyword"), Param("key", "Key")]


def _pair_words(n=70):
    return keywords("en", n, 4)


def _pair_gen(a, b):
    return lambda r: {a: r.choice(_pair_words()), b: r.choice(_pair_words())}


def _pair_attack(dec, a, b):
    def run(ct, lang="en"):
        w = _pair_words()
        return X.keyspace(lambda **k: dec(ct, **k), ({a: x, b: y} for x in w for y in w), lang, "keyword-pair dictionary")
    return run


def _quag(kind):
    def tables(alphabet):
        k = keyed_alphabet(alphabet)
        return (k, A) if kind == 1 else (A, k) if kind == 2 else (k, k)

    def enc(t, alphabet="SPRINGTIME", key="FLOWER"):
        pa, ca = tables(alphabet)
        ks = letters(key)
        return "".join(ca[(pa.index(c) + ca.index(ks[i % len(ks)])) % 26] for i, c in enumerate(letters(t)))

    def dec(t, alphabet="SPRINGTIME", key="FLOWER"):
        pa, ca = tables(alphabet)
        ks = letters(key)
        return "".join(pa[(ca.index(c) - ca.index(ks[i % len(ks)])) % 26] for i, c in enumerate(letters(t)))

    return enc, dec


for kind, name, desc in ((1, "Quagmire I", "keyed plain alphabet, straight cipher alphabet"), (2, "Quagmire II", "straight plain alphabet, keyed cipher alphabet")):
    e, d = _quag(kind)
    add(id=f"quagmire{kind}", name=name, family="Polyalphabetic", era="American Cryptogram Association", summary=f"Periodic cipher with a {desc}.", how="Each key letter picks a slide of the alphabets. The Quagmires are all ways of mixing a Vigenere table.", weakness="It remains periodic, so the IC reveals the period; keyword alphabets are guessable.",
        encrypt=e, decrypt=d, key={"alphabet": "SPRINGTIME", "key": "FLOWER"}, example="Quagmire tables mix alphabets", params=P2, attack=_pair_attack(d, "alphabet", "key"), attack_name="Keyword-pair dictionary", keygen=_pair_gen("alphabet", "key"))


def _nico(t, keyword, sign):
    t, o, out = letters(t), order(keyword), []
    k = len(o)
    return t, o, k, out


def nico_e(t, keyword="CIPHER"):
    t, o, k, out = _nico(t, keyword, 1)
    key = to_ints(keyword)
    for b in range(0, len(t), 5 * k):
        block = t[b:b + 5 * k]
        cols = {c: "".join(A[(A.index(x) + int(key[c])) % 26] for x in block[c::k]) for c in range(k)}
        out.append("".join(cols[c] for c in o))
    return "".join(out)


def nico_d(t, keyword="CIPHER"):
    t, o, k, out = _nico(t, keyword, -1)
    key = to_ints(keyword)
    for b in range(0, len(t), 5 * k):
        block, n, pos, grid = t[b:b + 5 * k], len(t[b:b + 5 * k]), 0, {}
        for c in o:
            h = n // k + (c < n % k)
            grid[c] = block[pos:pos + h]
            pos += h
        out.append("".join(A[(A.index(grid[c][r]) - int(key[c])) % 26] for r in range(n // k + 1) for c in range(k) if r < len(grid[c])))
    return "".join(out)


add(id="nicodemus", name="Nicodemus", family="Transposition", era="American Cryptogram Association", summary="Blocks transposed by column, with each column Vigenere-shifted.", how="The keyword both orders the columns and shifts them, and blocks are five rows deep.", weakness="One keyword controls both layers, so a dictionary attack needs only a single guess.",
    encrypt=nico_e, decrypt=nico_d, key={"keyword": "CIPHER"}, example="Two layers from one word", params=[Param("keyword", "Keyword")], attack=lambda ct, lang="en": X.keyspace(lambda keyword: nico_d(ct, keyword), X.word_keys("keyword", lang), lang, "keyword dictionary"), attack_name="Keyword dictionary", keygen=lambda r: {"keyword": dict_word(r)})


def _morse_stream(t):
    return "x".join(MORSE[c] for c in letters(t)) + "x"


def _unmorse(s):
    return "".join(UNMORSE.get(g, "") for g in s.split("x"))


TRIPLES = [a + b + c for a in ".-x" for b in ".-x" for c in ".-x" if a + b + c != "xxx"]


def fm_e(t, keyword="ROUNDTABLE"):
    s = _morse_stream(t)
    s += "x" * (-len(s) % 3)
    k = keyed_alphabet(keyword)
    return "".join(k[TRIPLES.index(s[i:i + 3])] for i in range(0, len(s) - 2, 3) if s[i:i + 3] != "xxx")


def fm_d(t, keyword="ROUNDTABLE"):
    k = keyed_alphabet(keyword)
    return _unmorse("".join(TRIPLES[k.index(c)] for c in letters(t) if k.index(c) < 26))


def fm_a(ct, lang="en"):
    return X.keyspace(lambda keyword: fm_d(ct, keyword), X.word_keys("keyword", lang), lang, "keyword dictionary")


add(id="fracmorse", name="Fractionated Morse", family="Fractionating", era="American Cryptogram Association", summary="Morse split into threes, each triple becoming a letter.", how="Letters are written in Morse with x as a separator, then cut into groups of three symbols and substituted with a keyed alphabet.", weakness="Triple frequencies keep the shape of Morse; word keys are guessable.",
    encrypt=fm_e, decrypt=fm_d, key={"keyword": "ROUNDTABLE"}, example="Dots and dashes in triples", params=[Param("keyword", "Keyword")], attack=fm_a, attack_name="Keyword dictionary", keygen=lambda r: {"keyword": dict_word(r)})


def _slide(t, key, dec):
    t, ks, out = letters(t), to_ints(key), []
    t += "X" * (len(t) % 2)
    for i in range(0, len(t), 2):
        k = int(ks[(i // 2) % len(ks)])
        a, b = A.index(t[i]), A.index(t[i + 1])
        if not dec:
            if (b - k) % 26 == a:
                out += [A[(a + 1) % 26], A[(a + 1 + k) % 26]]
            else:
                out += [A[(b - k) % 26], A[(a + k) % 26]]
        else:
            if (b - k) % 26 == a:
                out += [A[(a - 1) % 26], A[(a - 1 + k) % 26]]
            else:
                out += [A[(b - k) % 26], A[(a + k) % 26]]
    return "".join(out)


def sl_e(t, key="DIGRAPH"):
    return _slide(t, key, False)


def sl_d(t, key="DIGRAPH"):
    return _slide(t, key, True)


add(id="slidefair", name="Slidefair", family="Polygraphic", era="American Cryptogram Association", summary="Playfair's rectangle rule applied on sliding alphabets.", how="Each key letter slides a second alphabet under the first. A pair is replaced by the opposite corners of its rectangle.", weakness="It is periodic and works on pairs, so digraph statistics leak; keyword keys are guessable.",
    encrypt=sl_e, decrypt=sl_d, key={"key": "DIGRAPH"}, example="Sliding rows make rectangles", params=[Param("key", "Key")], attack=lambda ct, lang="en": X.keyspace(lambda key: sl_d(ct, key), X.word_keys("key", lang), lang, "keyword dictionary"), attack_name="Keyword dictionary", keygen=lambda r: {"key": dict_word(r)})


def _gromark_stream(primer, n):
    d = [int(c) for c in str(primer)]
    while len(d) < n:
        d.append((d[len(d) - len(str(primer))] + d[len(d) - len(str(primer)) + 1]) % 10)
    return d[:n]


def gr_e(t, alphabet="ENIGMA", primer="23452"):
    k = keyed_alphabet(alphabet)
    t = letters(t)
    return "".join(k[(A.index(c) + g) % 26] for c, g in zip(t, _gromark_stream(primer, len(t))))


def gr_d(t, alphabet="ENIGMA", primer="23452"):
    k = keyed_alphabet(alphabet)
    t = letters(t)
    return "".join(A[(k.index(c) - g) % 26] for c, g in zip(t, _gromark_stream(primer, len(t))))


def gr_a(ct, lang="en"):
    keys = ({"alphabet": w, "primer": f"{p:05d}"} for w in keywords(lang, 60, 4) for p in range(10000, 10600))
    return X.keyspace(lambda alphabet, primer: gr_d(ct, alphabet, primer), keys, lang, "alphabet words and a primer range")


add(id="gromark", name="Gromark", family="Polyalphabetic", era="W. J. Hall, American Cryptogram Association", summary="A keyed alphabet with a running numeric key grown from a five-digit primer.", how="Each new key digit is the sum, without carrying, of two earlier digits. That lagged Fibonacci idea appears in the VIC cipher too.", weakness="Primers number only 100,000. The demo searches a limited range and a word list, so it models a weak key choice.",
    encrypt=gr_e, decrypt=gr_d, key={"alphabet": "ENIGMA", "primer": "23452"}, example="Primers grow into keys", params=[Param("alphabet", "Alphabet keyword"), Param("primer", "Five-digit primer")], attack=gr_a, attack_name="Word list and primer range", keygen=lambda r: {"alphabet": r.choice(keywords("en", 60, 4)), "primer": f"{r.randrange(10000, 10600):05d}"})


def al_e(t, keyword="ALBERTI", period=5):
    k, p = keyed_alphabet(keyword), int(period)
    return "".join(k[(A.index(c) + i // p) % 26] for i, c in enumerate(letters(t)))


def al_d(t, keyword="ALBERTI", period=5):
    k, p = keyed_alphabet(keyword), int(period)
    return "".join(A[(k.index(c) - i // p) % 26] for i, c in enumerate(letters(t)))


add(id="alberti", name="Alberti disk", family="Polyalphabetic", era="Leon Battista Alberti, 1467", summary="The first polyalphabetic cipher: rotate the disk during the message.", how="A mixed inner ring sits against a plain outer ring. Every few letters the disk turns one place.", weakness="A keyword-mixed disk and regular turns can be guessed. Alberti turned it at irregular intervals, which is stronger.",
    encrypt=al_e, decrypt=al_d, key={"keyword": "ALBERTI", "period": 5}, example="Rotate the disk as you write", params=[Param("keyword", "Disk keyword"), Param("period", "Letters per turn", "int")],
    attack=lambda ct, lang="en": X.keyspace(lambda keyword, period: al_d(ct, keyword, period), ({"keyword": w, "period": p} for w in keywords(lang, 2500, 4) for p in (3, 5, 8, 10)), lang, "disk words and regular turn rates"), attack_name="Disk words and regular turn rates", keygen=lambda r: {"keyword": dict_word(r), "period": r.choice([3, 5, 8, 10])})

M209_SIZES = [26, 25, 23, 21, 19, 17]


def _m209_setup(seed):
    r = random.Random(int(seed))
    pins = [[r.randint(0, 1) for _ in range(s)] for s in M209_SIZES]
    bars = [tuple(r.sample(range(6), 2)) for _ in range(27)]
    return pins, bars


def _m209_stream(n, seed, start):
    pins, bars = _m209_setup(seed)
    st = [ord(c) - 65 for c in letters(start)]
    out = []
    for i in range(n):
        active = [pins[w][(st[w] + i) % M209_SIZES[w]] for w in range(6)]
        out.append(sum(1 for a, b in bars if active[a] or active[b]))
    return out


def m209(t, seed=1942, start="AAAAAA"):
    t = letters(t)
    return "".join(A[(25 - i + k) % 26] for i, k in zip((A.index(c) for c in t), _m209_stream(len(t), seed, start)))


def m209_demo(seed):
    a, b = "ATTACKTHEFORTATFIRSTLIGHTTOMORROW", "SENDAMMUNITIONANDFUELTOTHEBRIDGEX"
    ca, cb = m209(a, 1942, "QXAMPT"), m209(b, 1942, "QXAMPT")
    rec = "".join(A[(A.index(p) + A.index(x) - A.index(y)) % 26] for p, x, y in zip(a, ca, cb))
    return {"kind": "modern", "title": "Depth on the M-209", "steps": ["The M-209 is reciprocal, with C = key - P + 25. Reusing a setting makes two messages share one key stream.", f"First message begins {ca[:16]}.", "Because the key cancels, C1 - C2 equals P2 - P1. A guessed first message reveals the second. American and German analysts both exploited operator reuse."], "recovered": rec, "truth": b, "success": rec == b}


add(id="m209", name="M-209 (teaching model)", family="Machines", era="Hagelin, US Army, WWII and Korea", summary="A pocket mechanical cipher with six pin wheels and a lug cage.", how="Wheels of 26 to 17 pins step together. A cage of 27 bars counts how many engaged wheels push it, giving a shift for that letter. This model fixes pins and lugs from a seed; the key is the wheel start.", weakness="Long periods, but the key is not random. German analysts read it routinely when messages were sent in depth or with known text.",
    encrypt=m209, decrypt=m209, key={"seed": 1942, "start": "AAAAAA"}, example="Field message", params=[Param("seed", "Pin and lug seed", "int"), Param("start", "Six start letters")], demo_attack=m209_demo)
