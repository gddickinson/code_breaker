"""Round 63: the word-break pipeline on English texts outside Le Figaro."""
import json
import random

from codebreaker.mysteries import wordbreak_en as W


def test_words_and_plain_split():
    enc, plain = W.words_of("1916 train station robbery cryptogram")
    assert "there" in plain and "with" in plain
    assert ["t", "h", "x"] in enc and all(w not in plain for w in ("".join(x) for x in enc))


def test_share_refine_shuffle():
    words = [["a", "b", "c"]]
    assert W.share(words, {"a": "t", "b": "h", "c": "e"}) == 1.0
    s = W.shuffled([["a", "b"], ["c"]], random.Random(1))
    assert [len(w) for w in s] == [2, 1]


def test_recorded_no_reading_with_working_controls():
    r = json.loads(W.RESULT.read_text())
    assert r["passed"] == [] and all(x["gates"]["control"] for x in r["rows"])
