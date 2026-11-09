"""Ciphers that change the substitution alphabet as the message proceeds."""
import numpy as np

from .. import kernels as K
from ..attacks import classical as X
from ..languages import corpus_text, keywords
from ..text import A, keyed_alphabet, letters, to_ints, to_text
from .base import Param, add

FAM = "Polyalphabetic"
P_KEY = Param("key", "Keyword")


def _stream(n, key):
    k = np.asarray(key)
    return np.resize(k, n)


def vig_int(t, k):
    return (t - _stream(len(t), k)) % 26


def beau_int(t, k):
    return (_stream(len(t), k) - t) % 26


def var_int(t, k):
    return (t + _stream(len(t), k)) % 26


def porta_int(t, k):
    g = _stream(len(t), k) // 2
    return np.where(t < 13, ((t + g) % 13) + 13, (t - 13 - g) % 13)


def _family(fn):
    return lambda t, key="LEMON": to_text(fn(to_ints(t), to_ints(key)))


def word_gen(r):
    return {"key": r.choice(keywords("en", 2500, 5))}


def _attack(fn, shifts=26):
    return lambda ct, lang="en": X.periodic(ct, fn, lang, shifts)


ENTRIES = [
    ("vigenere", "Vigenere", "Bellaso 1553, misattributed to Vigenere", "Repeat a keyword and Caesar-shift each letter by the matching key letter.",
     "Called le chiffre indechiffrable for three centuries. Each key letter chooses one of 26 alphabets.",
     "The repeating key is the flaw. Kasiski (1863) and Babbage noticed that repeats reveal the period, after which each column is an easy Caesar.",
     var_int, vig_int, "Attack at dawn"),
    ("beaufort", "Beaufort", "Admiral Beaufort, 1857", "Subtract the plaintext from the key: C = K - P.",
     "It is reciprocal, so the same operation encrypts and decrypts.", "Same as Vigenere: a repeating key.", beau_int, beau_int, "Reciprocal by design"),
    ("variant", "Variant Beaufort", "19th century", "C = P - K, the mirror of Vigenere.",
     "It is equivalent to decrypting with Vigenere.", "Same as Vigenere: a repeating key.", vig_int, var_int, "Mirror of Vigenere"),
    ("porta", "Porta", "Giambattista della Porta, 1563", "Thirteen reciprocal alphabets, chosen in pairs by the key.",
     "Each key pair (AB, CD, ...) swaps the two halves of the alphabet with a slide.", "It has a repeating key and only 13 alphabets.", porta_int, porta_int, "Porta used thirteen tables"),
]
for cid, name, era, summary, how, weak, enc, dec, ex in ENTRIES:
    add(id=cid, name=name, family=FAM, era=era, summary=summary, how=how, weakness=weak, encrypt=_family(enc), decrypt=_family(dec), key={"key": "LEMON"},
        example=ex, params=[P_KEY], attack=_attack(dec), attack_name="Find the period with index of coincidence, then fit each column", keygen=word_gen)


def _digits(s):
    return np.array([int(c) for c in str(s)], dtype=np.int32)


def gron_e(t, key="31415"):
    return to_text(var_int(to_ints(t), _digits(key)))


def gron_d(t, key="31415"):
    return to_text(vig_int(to_ints(t), _digits(key)))


def gron_a(ct, lang="en"):
    r = X.periodic(ct, vig_int, lang, shifts=10)
    r["key"]["key"] = "".join(str(ord(c) - 65) for c in r["key"]["key"])
    return r


add(id="gronsfeld", name="Gronsfeld", family=FAM, era="Count Gronsfeld, 17th century", summary="Vigenere using a number as the key.",
    how="Each digit gives a shift of 0 to 9.", weakness="Only ten alphabets per position, and still periodic.", encrypt=gron_e, decrypt=gron_d, key={"key": "31415"},
    example="Digits as a key", params=[Param("key", "Digit key")], attack=gron_a, attack_name="Period search with ten candidate shifts",
    keygen=lambda r: {"key": "".join(str(r.randint(0, 9)) for _ in range(6))})


def tri_e(t):
    x = to_ints(t)
    return to_text((x + np.arange(len(x))) % 26)


def tri_d(t):
    x = to_ints(t)
    return to_text((x - np.arange(len(x))) % 26)


add(id="trithemius", name="Trithemius", family=FAM, era="Johannes Trithemius, 1508", summary="Shift by 0, 1, 2, 3 and so on: a progressive tableau.",
    how="The first printed book on cryptography introduced the tabula recta.", weakness="It has no key, so knowing the system is enough.", encrypt=tri_e, decrypt=tri_d, key={},
    example="Tabula recta", attack=lambda ct, lang="en": X.result(tri_d(ct), {}, "undo the progressive shift", lang), attack_name="Undo the fixed progression", keygen=lambda r: {})


def auto_e(t, key="QUEENLY"):
    p = to_ints(t)
    k = np.concatenate((to_ints(key), p))[: len(p)]
    return to_text((p + k) % 26)


def auto_d(t, key="QUEENLY"):
    return to_text(K.autokey_decrypt(to_ints(t), to_ints(key)))


add(id="autokey", name="Autokey", family=FAM, era="Bellaso and Vigenere, 16th century", summary="The message extends its own key, so nothing repeats.",
    how="After the short primer runs out, the plaintext itself becomes the key.", weakness="The key is language, so statistics leak. Climbing one primer letter at a time works, because a correct primer letter improves every later position it feeds.",
    encrypt=auto_e, decrypt=auto_d, key={"key": "QUEENLY"}, example="The key feeds itself", params=[P_KEY], attack=X.autokey, attack_name="Climb the primer one letter at a time", keygen=word_gen)


def book_key():
    return letters(corpus_text("en"))


def run_e(t, offset=2000):
    p, b = to_ints(t), to_ints(book_key())
    return to_text((p + b[int(offset):int(offset) + len(p)]) % 26)


def run_d(t, offset=2000):
    p, b = to_ints(t), to_ints(book_key())
    return to_text((p - b[int(offset):int(offset) + len(p)]) % 26)


add(id="running", name="Running key", family=FAM, era="19th-20th century", summary="Vigenere keyed by the text of a book.",
    how="Both parties agree a book and a starting point. Here the key book is our English corpus, and the key is the offset into it.",
    weakness="If the book can be guessed, slide along it. If not, plaintext and key are both language, and the pair can be teased apart statistically.",
    encrypt=run_e, decrypt=run_d, key={"offset": 2000}, example="Page twelve of the novel", params=[Param("offset", "Letter offset into the book", "int")],
    attack=X.running_key, attack_name="Slide along a candidate key book", keygen=lambda r: {"offset": r.randint(1000, 900000)})


def quag_e(t, alphabet="KRYPTOS", key="ABSCISSA"):
    a = keyed_alphabet(alphabet)
    k = [a.index(c) for c in letters(key)]
    return "".join(a[(a.index(c) + k[i % len(k)]) % 26] for i, c in enumerate(letters(t)))


def quag_d(t, alphabet="KRYPTOS", key="ABSCISSA"):
    a = keyed_alphabet(alphabet)
    k = [a.index(c) for c in letters(key)]
    return "".join(a[(a.index(c) - k[i % len(k)]) % 26] for i, c in enumerate(letters(t)))


add(id="quagmire", name="Quagmire III (keyed Vigenere)", family=FAM, era="ACA type; used in Kryptos, 1990", summary="Vigenere over a keyword-mixed alphabet.",
    how="Build the tableau from a mixed alphabet, then index it with a key. The first two sections of the Kryptos sculpture use it.",
    weakness="The period still shows up in the IC, and then the alphabet keyword can be guessed from a dictionary.",
    encrypt=quag_e, decrypt=quag_d, key={"alphabet": "KRYPTOS", "key": "PALIMPSEST"}, example="Between subtle shading", params=[Param("alphabet", "Alphabet keyword"), P_KEY],
    attack=lambda ct, lang="en": X.quagmire(ct, quag_d, lang), attack_name="Find the period, then search alphabet keywords",
    keygen=lambda r: {"alphabet": r.choice(keywords("en", 1500, 6)), "key": r.choice(keywords("en", 2500, 5))})

CHAO_L = "HXUCZVAMDSLKPEFJRIGTWOBNYQ"
CHAO_R = "PTLNBQDEOYSFAVZKGJRIHWXUMC"


def _chao(text, left, right, decrypt):
    l, r, out = list(left), list(right), []
    for c in letters(text):
        i = l.index(c) if decrypt else r.index(c)
        out.append(r[i] if decrypt else l[i])
        l = l[i:] + l[:i]
        r = r[i:] + r[:i]
        l = [l[0]] + l[2:14] + [l[1]] + l[14:]
        r = r[1:] + r[:1]
        r = r[:2] + r[3:14] + [r[2]] + r[14:]
    return "".join(out)


def chao_e(t, left=CHAO_L, right=CHAO_R):
    return _chao(t, keyed_alphabet(left), keyed_alphabet(right), False)


def chao_d(t, left=CHAO_L, right=CHAO_R):
    return _chao(t, keyed_alphabet(left), keyed_alphabet(right), True)


def chao_a(ct, lang="en"):
    words = keywords(lang, 90, 4)
    return X.keyspace(lambda left, right: chao_d(ct, left, right), ({"left": a, "right": b} for a in words for b in words), lang, "keyword pairs from a dictionary")


add(id="chaocipher", name="Chaocipher", family=FAM, era="John Byrne, 1918; published 2010", summary="Two alphabets that permute themselves after every letter.",
    how="Byrne challenged governments with it for decades. The mechanism stayed secret until his family gave his papers to the National Cryptologic Museum in 2010.",
    weakness="Depths and known plaintext expose it. Our demo only tries keyword-derived alphabets, which is a weak key choice.",
    encrypt=chao_e, decrypt=chao_d, key={"left": CHAO_L, "right": CHAO_R}, example="WELLDONEISBETTERTHANWELLSAID", params=[Param("left", "Left alphabet or keyword"), Param("right", "Right alphabet or keyword")],
    attack=chao_a, attack_name="Keyword-pair dictionary", keygen=lambda r: {"left": r.choice(keywords("en", 90, 4)), "right": r.choice(keywords("en", 90, 4))})
