"""Messages written in other scripts (Round 76): public script alphabets and a keyed rune substitution.

The alphabets use the sign tables of codebreaker.writing (recorded sources); spelling Latin letters with them is a
modern convention, as people do with runes or 'hieroglyph alphabets', and is an encoding, not a cipher. The rune
substitution is a real cipher: a keyword-mixed alphabet written onto 26 runes, solved like any simple substitution."""
from ..attacks import classical as X
from ..text import A, keyed_alphabet, letters
from ..writing.signs import tables
from ..writing.transliterate import read, write
from .base import Param, add
from .monoalphabetic import word_gen

FAM = "Scripts"


def _encoder(script):
    return lambda t: write(t, script)["text"]


def _decoder(t):
    return letters(read(t)["simple"])


for cid, script, name, era, extra in (
        ("runes", "runic", "Runic alphabet (Elder Futhark)", "Germanic peoples, c. 150-800 AD; modern rune spellings",
         "The Elder Futhark has 24 runes and no C, Q, V, X or Y, so those letters are spelled with K, W, KS and J."),
        ("ogham", "ogham", "Ogham", "Early Irish inscriptions, 4th-6th centuries AD",
         "Ogham's twenty letters are strokes across a stem line; the missing letters (K, P, Y, J, W, X, V) are spelled with near sounds."),
        ("hieroglyph_alphabet", "egyptian", "Hieroglyph alphabet", "Modern charts built on Egyptian uniliteral signs",
         "Egyptian wrote consonants only and never spelled words letter by letter; these charts use the 26 one-consonant signs, with E as a reed and O and U as a quail chick.")):
    add(id=cid, name=name, family=FAM, era=era,
        summary=f"Latin letters written with {name.split(' (')[0].lower()} signs: a public script, so no key.",
        how=f"Each letter becomes the sign with that sound in the recorded sign tables. {extra}",
        weakness="Anyone who knows the script, or has the Scripts & Glyphs page, can read it; letters the script lacks are merged, so some spellings change.",
        encrypt=_encoder(script), decrypt=_decoder, key={}, example="Isis and Ptah sit in Thinis",
        attack=lambda ct, lang="en": X.result(_decoder(ct), {}, "read the public script", lang), attack_name="Read the public script", keygen=lambda r: {})


def rune_set() -> str:
    """26 distinct runes: the 24 Elder Futhark runes from the recorded table, then the first two other rune letters."""
    t = tables()["runic"]
    elder = [ch for ch, e in t.items() if e.get("source") == "Elder Futhark table"]
    rest = [ch for ch, e in t.items() if ch not in elder and e.get("name", "").startswith("Runic Letter")]
    return "".join((elder + rest)[:26])


RUNES = rune_set()


def runesub_e(t, keyword=""):
    k = keyed_alphabet(letters(keyword))
    return "".join(RUNES[k.index(c)] if c in A else c for c in t.upper() if c in A or c == " ")


def runesub_d(t, keyword=""):
    k = keyed_alphabet(letters(keyword))
    return "".join(k[RUNES.index(c)] for c in t if c in RUNES)


def runesub_a(ct, lang="en"):
    syms = [c for c in ct if c in RUNES]
    return X.solve_symbols(syms, lang)


add(id="rune_substitution", name="Rune substitution", family=FAM, era="Puzzle books and treasure hunts; the idea of a secret alphabet is ancient",
    summary="A keyword-mixed alphabet written in runes: looks exotic, but is a simple substitution.",
    how="A keyword sets the order of the alphabet (keyword letters first, then the rest), and the n-th letter of that order is written with the n-th of 26 runes. The runes carry no sound here; they are just shapes.",
    weakness="Unusual symbols add no security: count them, relabel them as letters and solve by letter frequencies, exactly as for a simple substitution.",
    encrypt=runesub_e, decrypt=runesub_d, key={"keyword": "VALHALLA"}, example="Meet at the old bridge at dawn",
    params=[Param("keyword", "Keyword")], attack=runesub_a, attack_name="Relabel the symbols and anneal", keygen=word_gen)
