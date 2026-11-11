"""Round 83: acrostic and null-cipher finder, its controls and the worked examples."""
import json
import random

from codebreaker import acrostic as A
from codebreaker import acrostic_eval as E


def test_readings_and_letter_shuffle_for_unbroken_text():
    u = A._units("Alpha beta\nGamma delta\n")
    r = A.readings({"lines": ["Mild", "Echo"] * 5, "sentences": [], "words": ["x"] * 3})
    assert r["first letters of lines"] == "MEMEMEMEME"
    v = A._shuffled({"lines": [], "sentences": [], "words": ["abcdefghijkl"]}, random.Random(1))
    assert v["words"][0] != "ABCDEFGHIJKL" and sorted(v["words"][0]) == sorted("ABCDEFGHIJKL")
    assert u["lines"] == ["Alpha beta", "Gamma delta"]


def test_planted_every_nth_is_found_and_plain_text_is_not():
    rnd = random.Random(2)
    sents = E._sentences(rnd)
    r = A.find(E.every_nth("MEETMEATMIDNIGHT", 5, sents, rnd), langs=("en",))
    assert any("MEETMEATMIDNIGHT" in f["letters"] for f in r["findings"])
    assert not A.find("\n".join(rnd.sample(sents, 16)), langs=("en",))["findings"]


def test_recorded_controls_and_examples():
    r = json.loads(E.RESULT.read_text())
    assert r["plain_passages_with_findings"].startswith("0 of")
    assert r["positive_controls"]["null cipher"]["found"] >= 3
    assert r["hypnerotomachia"]["as printed (V for U)"]["p"] < 0.05
    assert set(r["dday"]["codewords"]) == {"UTAH", "OMAHA", "OVERLORD", "MULBERRY", "NEPTUNE"}
