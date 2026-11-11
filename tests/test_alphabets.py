"""Round 86: language models and ciphers over Cyrillic, Greek, Hebrew and Arabic-script alphabets. Skipped when the
corpora are absent (scripts/fetch_corpora.py el ru bg he; scripts/fetch_wiki_corpora.py)."""
import numpy as np
import pytest

from codebreaker import alphabets as AB
from codebreaker.attacks import alphabet as AT

have = set(AB.available())
need = lambda *c: pytest.mark.skipif(not set(c) <= have, reason="corpus not fetched")


def test_normalise_folds_variants():
    assert AB.normalise("Ἀθῆναι ΟΔΟΣ", "el") == "αθηναι οδοσ"
    assert AB.normalise("שָׁלוֹם מלך", "he") == "שלומ מלכ"
    assert AB.normalise("أَحْمَد", "ar") == "احمد" and AB.normalise("كتاب", "fa") == "کتاب"
    assert AB.normalise("Ёлка́", "ru") == "елка" and AB.normalise("Йод їжак", "uk") == "йод їжак"


def test_detect_script():
    assert AB.detect_script("Привет мир, как дела")[0] == "Cyrillic"
    assert AB.detect_script("hello world")[0] is None


@need("el")
def test_greek_alphabet_is_the_standard_24():
    assert AB.model("el")["alpha"] == "αβγδεζηθικλμνξοπρστυφχψω"


@need("he")
def test_hebrew_alphabet_is_the_standard_22():
    assert AB.model("he")["alpha"] == "אבגדהוזחטיכלמנסעפצקרשת"


def _passage(lang, n, seed):
    full = AB.to_ints(AB.held_out(lang), lang)
    i = int(np.random.default_rng(seed).integers(0, len(full) - n))
    return full[i:i + n]


@need("el", "he")
@pytest.mark.parametrize("lang,kind,key", [("el", "caesar", 5), ("he", "vigenere", [3, 9, 1, 14]), ("el", "substitution", None)])
def test_attacks_recover_planted_text(lang, kind, key):
    p = _passage(lang, 300, 1)
    A = len(AB.model(lang)["alpha"])
    if key is None:
        key = np.random.default_rng(2).permutation(A).tolist()
    c = AB.to_ints(AT.encrypt(AB.to_text(p, lang), lang, kind, key), lang)
    assert (AT.solve(c, lang, kind)["plain"] == p).mean() >= 0.95


@need("el")
def test_three_gates_on_a_greek_substitution_and_random_letters():
    """Greek, where the solver's positive control is strong (Hebrew's is not: its gate answers 'Inconclusive')."""
    A = len(AB.model("el")["alpha"])
    p = AB.to_text(_passage("el", 300, 3), "el")
    c = AT.encrypt(p, "el", "substitution", np.random.default_rng(4).permutation(A).tolist())
    r = AT.crack(c, ["el"])
    assert r["verdict"].startswith("Readable candidate")
    assert np.mean([x == y for x, y in zip(r["best"]["text"], p)]) >= 0.95  # rare letters may stay unpinned
    noise = AB.to_text(np.random.default_rng(5).integers(0, A, 300), "el")
    assert not AT.crack(noise, ["el"])["verdict"].startswith("Readable")
