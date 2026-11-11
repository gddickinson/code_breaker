"""Round 85b: extra cipher languages and the staged language choice. Rates measured over 18 languages x 15 passages
(scratchpad langeval.py, recorded in SESSION_LOG): top-3 hit rate at 150 / 400 letters was plain 1.00 / 1.00,
transposition 1.00 / 1.00, Vigenere 0.91 / 0.96, simple substitution 0.97 / 0.97 (8 passages each)."""
import random
import string

import pytest

from codebreaker import langchoice as LC
from codebreaker.languages import EXTRA, cipher_langs, corpus_text
from codebreaker.text import letters

A = string.ascii_uppercase
need = pytest.mark.skipif(not {"nl", "fi", "pl"} <= set(cipher_langs()), reason="extra corpora not fetched (scripts/fetch_corpora.py)")


def test_letters_fold_nordic_and_polish():
    assert letters("Łódź søster Þór đ ı") == "LODZSOSTERTHORDI"


def test_core_languages_unchanged():
    assert set(cipher_langs()) >= {"en", "fr", "de", "it", "es", "la"} and not set(EXTRA) & {"en", "fr", "de", "it", "es", "la"}


def _passage(code: str, n: int, seed: int) -> str:
    t = letters(corpus_text(code))
    i = random.Random(seed).randrange(len(t) - n)
    return t[i:i + n]


@need
def test_multi_book_corpus_kept_whole():
    assert len(corpus_text("nl")) > 1_000_000  # several books, each with its own Gutenberg header


@need
def test_plain_and_transposed_text():
    p = _passage("nl", 300, 1)
    assert LC.distances(p)[0] == "letters unchanged" and LC.choose(p)[0] == "nl"
    cols = [5, 2, 0, 6, 1, 3, 4]
    assert "nl" in LC.choose("".join(p[c::7] for c in cols))


@need
def test_substitution_is_solved_in_each_language():
    rnd = random.Random(2)
    for code in ("fi", "pl"):
        k = list(A)
        rnd.shuffle(k)
        c = _passage(code, 300, 3).translate(str.maketrans(A, "".join(k)))
        stage, d = LC.distances(c)
        assert stage == "substitution" and code in sorted(d, key=d.get)[:3]


@need
def test_vigenere_columns_fit_at_their_shift():
    p, key = _passage("fi", 400, 4), [3, 17, 8, 22, 11]
    c = "".join(A[(ord(x) - 65 + key[i % 5]) % 26] for i, x in enumerate(p))
    stage, d = LC.distances(c)
    assert stage.startswith("polyalphabetic, period 5") and "fi" in sorted(d, key=d.get)[:3]


def test_short_text_falls_back():
    assert LC.choose("ABC DEF") == ["en", "fr", "de"]
