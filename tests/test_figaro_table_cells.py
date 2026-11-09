"""Blank-cell inference: token parsing, recorded control, and the hand-read family ads."""
import json

from codebreaker.languages import ROOT
from codebreaker.mysteries import figaro_digit_family as X, figaro_table_cells as C
from codebreaker.mysteries.figaro_digit_words import HAND

H = json.loads(HAND.read_text())


def key(tid, **extra):
    return {**next(t for t in X.digit_tables() if t["id"] == tid)["key"], **extra}


def test_numeric_tokens_split_words_and_keep_clear_letters():
    assert C.numeric_tokens(["5.16m16 : 12"]) == [["5", "16", "M", "16"], ["12"]]


def test_word_marks_unknown_only_in_mixed_mode():
    assert C.word(["1", "A"], {"1": "B"}, False) == "B."
    assert C.word(["1", "A"], {"1": "B"}, True) == "BA"


def test_infer_recovers_a_hidden_symbol():
    ads = [[list("9OIX"), list("9ILLE"), list("9ENIR")]] * 2
    got = C.infer(ads, {c: c for c in "OIXLENR"}, "9", False)
    assert got["letter"] == "V"


def test_infer_abstains_without_evidence():
    assert C.infer([[list("9X")]], {"X": "X"}, "9", False) is None


def test_family_transcriptions_read():
    got = X.apply(H["1883_18831230-R.jpg"]["words"], key("2119", R="O"))
    assert got[:3] == ["MARI", "PAS", "CONTENT"]
    got = X.apply(H["1887_18870125-2F.jpg"]["words"], key("2402"))
    assert got[:2] == ["COEUR", "TOUJOURS"]


def test_recorded_control_precision():
    r = json.loads((ROOT / "data/results/figaro_table_cells.json").read_text())
    assert r["correct"] >= 0.7 * r["answered"] and r["answered"] >= 30
