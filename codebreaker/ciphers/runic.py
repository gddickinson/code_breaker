"""Viking-age rune ciphers (Round 77b): branch runes (ætt and position) and the futhark shift of the Rök runestone.

Sources (data/sources/scripts): the Younger Futhark page gives the 16 runes in Viking-age order with their values, in
long-branch and short-twig forms; the 'Cipher runes' page gives the rule (the number of the ætt and of the rune within
it; Freyr's and Tyr's ætts often counted backwards); the Rök runestone page gives the stone's runes with each cipher
resolved, which the tests reproduce. The Younger Futhark did not mark voicing (recorded), so G, D, P, V are written with
K, T, B, F; writing E as I and O, W, Y as U, and C, Q as K is our convention for modern text."""
import re
from functools import lru_cache

from ..attacks import classical as X
from ..languages import ROOT
from ..text import letters
from ..writing.wikitext import clean, rows
from .base import Param, add

SRC = ROOT / "data/sources/scripts"
AETTS = (6, 5, 5)  # f u þ ą r k | h n i a s | t b m l ʀ (Cipher runes page)
LATIN = {"C": "k", "D": "t", "E": "i", "G": "k", "J": "i", "O": "u", "P": "b", "Q": "k", "V": "f", "W": "u", "X": "ks", "Y": "u", "Z": "s"}
BACK = {"þ": "TH", "ą": "A", "ʀ": "R"}


@lru_cache(maxsize=1)
def younger() -> tuple[list[str], dict, list[str]]:
    """The 16 values in order, {rune: index} for long-branch and short-twig forms, and the long-branch row."""
    text = (SRC / "wp_younger_futhark.txt").read_text()
    rs = [[clean(c) for c in r] for r in rows(text)]
    values, index, long_row = None, {}, None
    for a, b in zip(rs, rs[1:]):
        if len(a) == 16 and len(b) == 16 and all(len(x) == 1 and 0x16A0 <= ord(x) <= 0x16F8 for x in a):
            values, long_row = b, long_row or a
            for i, r in enumerate(a):
                index.setdefault(r, i)
    return values, index, long_row


def to_index(text: str) -> list[int | None]:
    """Latin letters as Younger Futhark positions (None keeps a word break)."""
    vals = younger()[0]
    out = []
    for c in text.upper():
        if c == " ":
            out.append(None)
        elif c.isalpha() and c.isascii():
            for v in LATIN.get(c, c.lower()):
                out.append(vals.index(v))
    return out


def from_index(ix: list[int | None]) -> str:
    vals = younger()[0]
    return "".join(" " if i is None else BACK.get(vals[i], vals[i].upper()) for i in ix)


def aett_pos(i: int, backwards: bool) -> tuple[int, int]:
    start = 0
    for a, n in enumerate(AETTS):
        if i < start + n:
            return (3 - a if backwards else a + 1), i - start + 1
        start += n
    raise ValueError(i)


def from_aett_pos(aett: int, pos: int, backwards: bool) -> int:
    a = 3 - aett if backwards else aett - 1
    return sum(AETTS[:a]) + pos - 1


def branch_e(t, backwards="yes"):
    bw = str(backwards).lower().startswith("y")
    return " ".join("/" if i is None else "%d:%d" % aett_pos(i, bw) for i in to_index(t)).replace(" / ", " / ")


def branch_d(t, backwards="yes"):
    bw = str(backwards).lower().startswith("y")
    out = []
    for tok in t.split():
        m = re.fullmatch(r"(\d):(\d)", tok)
        if m:
            out.append(from_aett_pos(int(m.group(1)), int(m.group(2)), bw))
        elif tok == "/":
            out.append(None)
    return from_index(out)


def branch_a(ct, lang="en"):
    return X.keyspace(lambda backwards: branch_d(ct, backwards), ({"backwards": b} for b in ("yes", "no")), lang, "tried both ætt orders")


add(id="branch_runes", name="Branch runes (cipher runes)", family="Scripts", era="Viking Age, e.g. the Rök runestone, c. 800 AD",
    summary="Each rune written as two numbers: its ætt (group) and its place in that group.",
    how="The 16 Younger Futhark runes form three ætts: f u þ ą r k, h n i a s and t b m l ʀ. A rune becomes its ætt number "
        "(strokes on the left of a stem) and its position (strokes on the right); here written as 'ætt:position'. Carvers "
        "often counted Freyr's and Tyr's ætts backwards, as on the Rök stone.",
    weakness="It is a Polybius square with three rows: the pairs are a simple substitution, and there are only two ætt orders to try.",
    encrypt=branch_e, decrypt=branch_d, key={"backwards": "yes"}, example="sakum mukmini",
    params=[Param("backwards", "Count the ætts backwards (yes/no)", "choice", ["yes", "no"])], attack=branch_a,
    attack_name="Try both ætt orders", keygen=lambda r: {"backwards": r.choice(["yes", "no"])})


def shift_e(t, shift=1):
    vals = younger()[0]
    long_row = sorted(younger()[1], key=lambda r: younger()[1][r])[:0]  # unused; runes come from the index below
    runes = {i: r for r, i in sorted(younger()[1].items(), key=lambda kv: -ord(kv[0]))}
    return "".join(" " if i is None else runes[(i + int(shift)) % 16] for i in to_index(t))


def shift_d(t, shift=1):
    index = younger()[1]
    return from_index([None if c == " " else (index[c] - int(shift)) % 16 for c in t if c == " " or c in index])


def shift_a(ct, lang="en"):
    return X.keyspace(lambda shift: shift_d(ct, shift), ({"shift": s} for s in range(16)), lang, "tried all 16 shifts")


add(id="futhark_shift", name="Futhark shift (Rök runestone)", family="Scripts", era="Viking Age, the Rök runestone, c. 800 AD",
    summary="A Caesar shift along the 16-rune row: each rune is written as a neighbour.",
    how="The Rök stone writes part of its text with each rune replaced by the one before it in the futhark (the reader "
        "takes the next rune to recover it). Here the shift is a key from 0 to 15.",
    weakness="Only 16 shifts exist; trying them all and keeping the one that reads breaks it at once.",
    encrypt=shift_e, decrypt=shift_d, key={"shift": 15}, example="sakum mukmini",
    params=[Param("shift", "Shift (0-15)", "int")], attack=shift_a, attack_name="Try all 16 shifts",
    keygen=lambda r: {"shift": r.randrange(1, 16)})


def rok_pairs() -> dict:
    """The resolved ciphers recorded for the Rök stone: ætt:position pairs and shifted runs."""
    t = (SRC / "wp_rok.txt").read_text()
    pairs = [(int(a), int(b), r) for a, b, r in re.findall(r"\[(\d):(\d) = (\S)\]", t)]
    shifts = [(c, p) for c, p in re.findall(r"\[([ᚠ-ᛸ]{4,}) = ([ᚠ-ᛸ]{4,})\]", t)]
    return {"pairs": pairs, "shifts": shifts}
