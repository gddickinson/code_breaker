"""Round 56: word-aware refinement under a matched null."""
import json
import random

from codebreaker.mysteries import figaro_wordrefine as W


def test_word_share_and_refine():
    words = [["a", "b"], ["c", "d", "e"]]
    key = {"a": "x", "b": "e", "c": "m", "d": "o", "e": "i"}
    assert W.word_share(words, key) == 3 / 5  # 'moi' is a word, 'xe' is not
    assert W.word_share(words, W.refine(words, key)) >= 3 / 5


def test_shuffle_keeps_word_lengths():
    words = [["1", "2"], ["3", "4", "5"]]
    s = W.shuffled_words(words, random.Random(1))
    assert [len(w) for w in s] == [2, 3] and sorted(c for w in s for c in w) == ["1", "2", "3", "4", "5"]


def test_recorded_gates():
    r = json.loads(W.RESULT.read_text())
    for k in ("jane", "b"):
        assert r[k]["gates"]["passed"] and r[k]["refined_share"] > max(n["refined"] for n in r[k]["null"])
    assert "baisers" in r["b"]["readings"]["1883_18830101-B.jpg"]
