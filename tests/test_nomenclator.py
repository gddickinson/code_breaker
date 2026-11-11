"""Round 88a: archive ciphers with homophones, nulls, word dividers and nomenclator code words."""
import random

from codebreaker.attacks import nomenclator as N
from codebreaker.nomenclator_eval import make, score


def test_tokens_split_numbers_and_characters():
    assert N.tokens("12 45 3. 77 08") == ["12", "45", "3", "77", "08"]
    assert N.tokens("AB CD") == ["A", "B", "C", "D"]


def test_caps_keep_code_words_rare_and_nulls_few():
    words = N.code_words("en", 40)
    cap = N.caps("en", words, 600)
    assert cap[0] == 600 and cap[N.NULL] == 18
    assert cap[27 + words.index("THE")] > cap[27 + len(words) - 1] >= 2


def test_divider_found_from_spacing():
    c = make("en", 600, random.Random(3), nulls=False, divider=True, n_code=0)
    d = N.find_divider(c["tokens"], "en")
    assert d["divider"] and d["symbol"] == c["divider"]


def test_homophonic_with_nulls_and_code_words_beats_letters_only():
    c = make("en", 600, random.Random(7), nulls=True, divider=False, n_code=10)
    full = score(N.solve(c["tokens"], "en"), c)["symbols_right"]
    plain = score(N.solve(c["tokens"], "en", n_words=0, nulls=False), c)["symbols_right"]
    assert full >= 0.85 and full >= plain


def test_one_symbol_per_code_word():
    c = make("en", 600, random.Random(7), nulls=False, divider=False, n_code=10)
    r = N.solve(c["tokens"], "en")
    words = [x for x in r["key"].values() if x not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" and x != "(null)"]
    assert len(words) == len(set(words))
